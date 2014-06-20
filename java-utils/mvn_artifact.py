#!/usr/bin/python
# Copyright (c) 2014, Red Hat, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the
#    distribution.
# 3. Neither the name of Red Hat nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# Authors:  Michal Srb <msrb@redhat.com>

from __future__ import print_function

import javapackages.metadata.pyxbmetadata as m
from javapackages.metadata.metadata import Metadata, MetadataInvalidException
from javapackages.metadata.artifact import MetadataArtifact
from javapackages.metadata.dependency import MetadataDependency

from javapackages.maven.artifact import Artifact, ArtifactFormatException
from javapackages.maven.pom import POM, PomLoadingException

from javapackages.xmvn.xmvn_resolve import XMvnResolve, ResolutionResult, ResolutionRequest

import sys
import os
import traceback
import pyxb
import lxml.etree
from optparse import OptionParser


usage="usage: %prog [options] <MVN spec | POM path> [artifact path]"
epilog="""
MVN spec:
Specification of Maven artifact in following format:

    groupId:artifactId[:extension[:classifier]][:version]

Wildcards (*) and empty parts in specifications are allowed (treated as wildcard).
JAR path must also be specified if this option is used.

Examples of valid specifications:
commons-lang:commons-lang:1.2
commons-lang:commons-lang:war:
commons-lang:commons-lang:war:test-jar:
commons-lang:commons-lang:war:test-jar:3.1
*:commons-lang (equivalent to ':commons-lang')

POM path:
Path where POM file is located.

Artifact path:
Path where Artifact file (usually JAR) is located.
"""


config = ".xmvn-reactor"


class ExtensionsDontMatch(Exception):
    pass


class UnknownVersion(Exception):
    pass


def get_parent_pom(pom):
    req = ResolutionRequest(pom.groupId, pom.artifactId,
                            extension="pom", version=pom.version)
    result = XMvnResolve.process_raw_request([req])[0]
    if not result:
        raise Exception("Unable to resolve parent POM")

    return POM(result.artifactPath)


def is_it_ivy_file(fpath):
    """Try to determine whether file in given path is Ivy file or not"""
    et = lxml.etree.ElementTree()
    doc = et.parse(fpath)

    return doc.tag == "ivy-module"


def add_artifact_elements(root, art, ppath=None, jpath=None):
    artifacts = []
    ext_backup = art.extension
    for path in [ppath, jpath]:
        if path:
            if path is ppath:
                if not is_it_ivy_file(ppath):
                    art.extension = "pom"
                else:
                    art.extension = os.path.splitext(pom_path)[1][1:]
                    art.properties['type'] = 'ivy'
            else:
                art.extension = ext_backup

            art.path = os.path.abspath(path)
            a = art.to_metadata()
            artifacts.append(a)

    if root.artifacts is None:
        root.artifacts = pyxb.BIND(*artifacts)
    else:
        for a in artifacts:
            root.artifacts.append(a)


def resolve_deps(deps):
    reqs = []
    unresolvable = []
    for d in deps:
        reqs.append(ResolutionRequest(d.groupId, d.artifactId,
                                      extension=d.extension,
                                      classifier=d.classifier,
                                      version=d.requestedVersion))
    results = XMvnResolve.process_raw_request(reqs)
    for i, r in enumerate(results):
        if r:
            if r.compatVersion and r.compatVersion != "SYSTEM":
                deps[i].resolvedVersion = r.compatVersion
            if r.namespace:
                deps[i].namespace = r.namespace
        else:
            unresolvable.append(deps[i])
    return unresolvable


def merge_sections(main, update):
    for upd in update:
        for curr in main:
            if curr.compare_to(upd):
                curr.merge_with(upd)
                break
        else:
            main.append(upd)


def gather_dependencies(pom_path):
    if not pom_path:
        return []
    pom = POM(pom_path)
    deps, depm, props = _get_dependencies(pom)

    parent = pom.parent
    while parent:
        ppom = None
        if parent.relativePath:
            try:
                ppom_path = os.path.join(os.path.dirname(pom._path), parent.relativePath)
                ppom = POM(ppom_path)
            except PomLoadingException:
                pass
        if not ppom:
            ppom = get_parent_pom(parent)

        parent = ppom.parent
        pdeps, pdepm, pprops = _get_dependencies(ppom)

        # merge "dependencies" sections
        merge_sections(deps, pdeps)
        # merge "dependencyManagement" sections
        merge_sections(depm, pdepm)

        # merge "properties" sections
        for pkey in pprops:
            if pkey not in props:
                props[pkey] = pprops[pkey]

    # apply dependencyManagement on deps
    for d in deps:
        for dm in depm:
            if d.compare_to(dm):
                d.merge_with(dm)
                break

    # only deps with scope "compile" or "runtime" are interesting
    deps = [x for x in deps if x.scope in ["", "compile", "runtime"]]

    for d in deps:
        d.interpolate(props)

    return deps


def _get_dependencies(pom):
    deps = []
    depm = []
    props = {}

    deps.extend([x for x in pom.dependencies])
    depm.extend([x for x in pom.dependencyManagement])
    props = pom.properties

    return deps, depm, props


if __name__ == "__main__":
    OptionParser.format_epilog = lambda self, formatter: self.epilog
    parser = OptionParser(usage=usage,
                        epilog=epilog)
    parser.add_option("--skip-dependencies", action="store_true", default=False,
                      help="skip dependencies section in resulting metadata")
    for index, arg in enumerate(sys.argv):
        sys.argv[index] = arg.decode(sys.getfilesystemencoding())

    (options, args) = parser.parse_args()
    if len(args) < 1:
        parser.error("At least 1 argument is required")

    try:
        uart = Artifact.from_mvn_str(args[0])
        uart.validate(allow_backref=False)
        if len(args) == 1:
            parser.error("When using artifact specification artifact path must be "
                         "provided")
        if not (uart.groupId and uart.artifactId and uart.version):
            parser.error("Defined artifact has to include at least groupId, "
                         "artifactId and version")
    except (ArtifactFormatException):
        uart = POM(args[0])
        pom_path = args[0]
    else:
        pom_path = None

    art = MetadataArtifact(uart.groupId, uart.artifactId, version=uart.version)
    if hasattr(uart, "extension") and uart.extension:
        art.extension = uart.extension
    if hasattr(uart, "classifier") and uart.classifier:
        art.classifier= uart.classifier

    jar_path = None
    if len(args) > 1:
        jar_path = args[1]
        extension = (os.path.splitext(jar_path)[1])[1:]
        if hasattr(art, "extension") and art.extension and art.extension != extension:
            raise ExtensionsDontMatch("Extensions don't match: '%s' != '%s'" % (art.extension, extension))
        else:
            art.extension = extension
    else:
        art.extension = "pom"

    if os.path.exists(config):
        xml = open(config).read()
        metadata = m.CreateFromDocument(xml)
    else:
        metadata = m.metadata()

    if not options.skip_dependencies and pom_path:
        deps = []
        mvn_deps = gather_dependencies(pom_path)
        for d in mvn_deps:
            deps.append(MetadataDependency.from_mvn_dependency(d))
            unavail = resolve_deps(deps)
            if unavail:
                unavail_str = ';'.join([x.get_mvn_str() for x in unavail])
                art.properties['maven.req.check.deps'] = unavail_str
        art.dependencies = set(deps)
    else:
        art.properties['xmvn.resolver.disableEffectivePom'] = 'true'

    add_artifact_elements(metadata, art, pom_path, jar_path)

    with open(config, 'w') as f:
        dom = metadata.toDOM(None)
        f.write(dom.toprettyxml(indent="   "))
