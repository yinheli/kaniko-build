# -*- coding: utf-8 -*-
import os
import click
import subprocess
import json

from kanikobuild.worker import Worker

# document
#  https://click.palletsprojects.com/en/8.1.x/
#  https://jinja.palletsprojects.com/en/3.1.x/


@click.group()
def cli():
    """kaniko build tool"""
    pass


default_mirrors = [
    "docker.mirrors.sjtug.sjtu.edu.cn",
    "mirror.baidubce.com",
    "hub-mirror.c.163.com",
    "registry-1.docker.io",
]


@cli.command(no_args_is_help=True)
@click.option("-n", "--namespace", default="default", help="namespace")
@click.option("-s", "--source", default="", help="source dir or git repo url")
@click.option("-d", "--destination", multiple=True, help="image destination")
@click.option("--buildarg", default="", help="build-args")
@click.option("--git", default="", help="git branch")
@click.option("--subpath", default="", help="Dockerfile path")
@click.option("--dockerfile", default="Dockerfile")
@click.option("-m", "--mirror", default=default_mirrors, multiple=True, help=f"registry mirror, support mutiple, default: {', '.join(default_mirrors)}")
@click.option("--insecure-pull", is_flag=True, help="set this flag if you want to pull images from a plain HTTP registry")
@click.option("--cache-repo", default="", help="set this flag to specify a remote repository that will be used to store cached layers")
@click.option("--insecure", is_flag=True, help="set this flag if you want to push images to a plain HTTP registry")
@click.option("--cleanup", is_flag=True, help="set this flag to clean the filesystem at the end of the build")
def build(**kwargs):
    """
    build image

    read more: https://github.com/GoogleContainerTools/kaniko
    """
    worker = Worker(**kwargs)
    worker.build()


@cli.command()
@click.option("-n", "--namespace", default="default", help="namespace")
@click.option("--all", is_flag=True, help="delete all build resource include pvc/pv (for cache)")
def cleanup(**kwargs):
    """cleanup"""
    worker = Worker(**kwargs)
    worker.cleanup()
