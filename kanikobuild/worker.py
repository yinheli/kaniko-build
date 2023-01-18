# -*- coding: utf-8 -*-

import os
import click
import subprocess
import json
from jinja2 import Environment, FileSystemLoader


class Worker:
    def __init__(self, **kwargs):
        self.namespace = kwargs.get("namespace", "default")
        self.workspace_pvc = "image-build-pvc"
        self.resource_base_dir = os.path.join(
            os.path.dirname(__file__), "resource",
        )
        self.source = kwargs.get("source", "")
        self.git = kwargs.get("git", "master")
        self.subpath = kwargs.get("subpath", "/")
        self.dockerfile = kwargs.get("dockerfile", "Dockerfile")
        self.destination = kwargs.get("destination", "")
        self.buildarg = kwargs.get("buildarg", "")
        self.source_base_dir = os.path.basename(self.source)

    def build(self):
        self.prepare()
        context = self.source
        if os.path.exists(self.source):
            context = f"dir:///workspace/source/{self.source_base_dir}"

        env = Environment(loader=FileSystemLoader(
            searchpath=self.resource_base_dir))
        tp = env.get_template('pod.yaml')

        args = {
            'context': context,
            'git': self.git,
            'subpath': self.subpath,
            'dockerfile': self.dockerfile,
            'buildarg': self.buildarg,
            'destination': self.destination
        }

        data = tp.render(args)

        click.echo("create build job")
        ret = self._kubectl("create", "-f", "-",
                            input=data.encode(), stdout=subprocess.PIPE)
        name = ret.stdout.decode("utf-8").strip().split(" ")[0]

        clearup = True

        try:
            self._kubectl("wait", "--for=condition=Ready",
                          "--timeout=120s", name)
            click.echo("run build job following log")
            self._kubectl("logs", "--follow", name)
        except KeyboardInterrupt:
            cleanup = click.confirm(
                "Your image is building, would you want to stop and cleanup? ", default=False)
        finally:
            if cleanup:
                click.echo("delete build job")
                self._kubectl("delete", name, "--grace-period=1")

    def cleanup(self):
        self._kubectl("delete", "pod", "-l", "app=kaniko-builder",
                      "--grace-period=1", "--wait=true", "--ignore-not-found")

    def prepare(self):
        if not self.source and not self.destination:
            click.echo("invalid source & destination")
            exit(1)

        self._prepare_pvc()
        self._prepare_workspace()

    def _prepare_pvc(self):
        if self._pvc_exists():
            return
        file = os.path.join(self.resource_base_dir, "prepare", "pvc.yaml")
        click.echo(f"create workspace pvc: {self.workspace_pvc}, file: {file}")
        self._kubectl("apply", "-f", file)

    def _pvc_exists(self) -> bool:
        ret = self._kubectl("get", "pvc", "-o", "json", stdout=subprocess.PIPE)
        pvcs = [x.get("metadata").get("name")
                for x in json.loads(ret.stdout).get("items")]

        return self.workspace_pvc in pvcs

    def _prepare_workspace(self):
        if not os.path.exists(self.source):
            return

        file = os.path.join(self.resource_base_dir, "prepare", "pod.yaml")
        click.echo("prepare workspace, copy files")
        ret = self._kubectl("create", "-f", file, stdout=subprocess.PIPE)
        name = ret.stdout.decode("utf-8").strip().split(" ")[0]
        name = name.removeprefix('pod/')
        # wait ready
        self._kubectl("wait", "--for=condition=Ready", f"pod/{name}")

        # copy file
        self._kubectl("exec", name, "--", "rm", "-rvf", "/workspace/source")
        self._kubectl("exec", name, "--", "mkdir", "/workspace/source")
        self._kubectl("cp", self.source, f"{name}:/workspace/source")
        self._kubectl("exec", name, "--", "ls",
                      f"/workspace/source/{self.source_base_dir}")

        self._kubectl("delete", "pod", name, "--grace-period=1")

    def _kubectl(self, *args, **kwargs):
        args = ["kubectl", "-n", self.namespace, *args]
        click.echo(f"execute: {' '.join(args)}")
        ret = subprocess.run(args, **kwargs)
        if ret.returncode != 0:
            raise Exception(f"kubectl fail {ret.returncode} {ret.stderr}")
        return ret
