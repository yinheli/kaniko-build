# -*- coding: utf-8 -*-

import os
import click
import subprocess
import json
from jinja2 import Environment, FileSystemLoader


class Worker:
    def __init__(self, **kwargs):
        self.namespace = kwargs.get("namespace", "default")
        self.workspace_pvc = None
        self.cache_pvc = 'kaniko-builder-cache'
        self.resource_base_dir = os.path.join(
            os.path.dirname(__file__), "resource",
        )
        self.source = kwargs.get("source", "")
        self.git = kwargs.get("git", "master")
        self.subpath = kwargs.get("subpath", "/")
        self.dockerfile = kwargs.get("dockerfile", "Dockerfile")
        self.destination = kwargs.get("destination", [])
        self.insecure = kwargs.get("insecure", False)
        self.buildarg = kwargs.get("buildarg", "")
        self.source_base_dir = os.path.basename(self.source)
        self.mirrors = kwargs.get("mirror", ["registry-1.docker.io"])
        self.insecurePull = kwargs.get("insecure_pull", False)
        self.arg_cleanup = kwargs.get("cleanup", False)
        self.all = kwargs.get("all", False)

        self.env = Environment(loader=FileSystemLoader(
            searchpath=self.resource_base_dir))

    def build(self):
        self.prepare()
        context = self.source
        if os.path.exists(self.source):
            context = f"dir:///workspace/source/{self.source_base_dir}"

        args = {
            'mirrors': self.mirrors,
            "insecurePull": self.insecurePull,
            'context': context,
            'git': self.git,
            'subpath': self.subpath,
            'dockerfile': self.dockerfile,
            'buildarg': self.buildarg,
            'destination': self.destination,
            'insecure': self.insecure,
            'pvc': self.workspace_pvc,
            'arg_cleanup': self.arg_cleanup,
        }

        # print(self._render('pod.yaml', args).decode("utf-8"))

        click.echo("create build job")
        ret = self._kubectl("create", "-f", "-",
                            input=self._render('pod.yaml', args), stdout=subprocess.PIPE)
        name = ret.stdout.decode("utf-8").strip().split(" ")[0]

        cleanup = True

        try:
            self._kubectl("wait", "--for=condition=Ready",
                          "--timeout=300s", name)
            click.echo("run build job following log")
            self._kubectl("logs", "--follow", name)
        except KeyboardInterrupt:
            cleanup = click.confirm(
                "Your image is building, would you want to stop and cleanup? ", default=False)
        finally:
            if cleanup:
                click.echo("delete build job")
                self._kubectl("delete", name, "--grace-period=1")
                if self.workspace_pvc:
                    self._kubectl("delete", "pvc", self.workspace_pvc)

    def cleanup(self):
        self._kubectl("delete", "pod,pvc", "-l", "app=kaniko-builder",
                      "--grace-period=1", "--wait=true", "--ignore-not-found")
        if self.all:
            self._kubectl("delete", "pvc", "kaniko-builder-cache",
                          "--grace-period=1", "--wait=true", "--ignore-not-found")

    def prepare(self):
        if not self.source and not self.destination:
            click.echo("invalid source & destination")
            exit(1)

        self._prepare_cache_pvc()
        self._prepare_workspace()

    def _prepare_cache_pvc(self):
        if self._pvc_exists(self.cache_pvc):
            return
        file = os.path.join(self.resource_base_dir,
                            "prepare", "pvc-cache.yaml")
        click.echo(f"create cache pvc: {self.cache_pvc}")
        self._kubectl("apply", "-f", file)

    def _pvc_exists(self, name) -> bool:
        ret = self._kubectl("get", "pvc", "-o", "json", stdout=subprocess.PIPE)
        pvcs = [x.get("metadata").get("name")
                for x in json.loads(ret.stdout).get("items")]

        return name in pvcs

    def _prepare_workspace(self):
        if not os.path.exists(self.source):
            return

        pvc = os.path.join(self.resource_base_dir,
                           "prepare", "pvc-source.yaml")
        ret = self._kubectl("create", "-f", pvc, stdout=subprocess.PIPE)
        name = ret.stdout.decode("utf-8").strip().split(" ")[0]
        name = name.removeprefix('persistentvolumeclaim/')
        self.workspace_pvc = name

        pod = os.path.join(self.resource_base_dir, "prepare", "pod.yaml")
        click.echo(f"prepare workspace, copy files, pvc: {self.workspace_pvc}")
        ret = self._kubectl("create", "-f", "-",
                            input=self._render(
                                'prepare/pod.yaml', {'pvc': self.workspace_pvc}),
                            stdout=subprocess.PIPE)
        name = ret.stdout.decode("utf-8").strip().split(" ")[0]
        name = name.removeprefix('pod/')
        # wait ready
        self._kubectl("wait", "--for=condition=Ready",
                      "--timeout=300s", f"pod/{name}")

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

    def _render(self, tpl, args):
        t = self.env.get_template(tpl)
        return t.render(args).encode()
