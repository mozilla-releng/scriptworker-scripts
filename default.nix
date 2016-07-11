{ pkgSrc ? { outPath = ./.; name = "source"; }
, pkgs ? import <nixpkgs> {}
}:

let
  python = import ./requirements-dev.nix { inherit pkgs; };
  version = pkgs.lib.removeSuffix "\n" (builtins.readFile ./version.txt);
in python.mkDerivation {
  name = "signingscript-${version}";
  src = pkgSrc;
  buildInputs = [
    python.pkgs."coverage"
    python.pkgs."flake8"
    python.pkgs."pytest"
    python.pkgs."pytest-cov"
  ];
  propagatedBuildInputs = [
    python.pkgs."arrow"
    python.pkgs."python-jose"
    python.pkgs."scriptworker"
    python.pkgs."signtool"
    python.pkgs."taskcluster"
  ];
  doCheck = false;
  checkPhase = ''
    export NO_TESTS_OVER_WIRE=1
    export PYTHONDONTWRITEBYTECODE=1
    flake8 scriptworker
    py.test --cov=scriptworker --cov-report term-missing
    coverage html
  '';
  passthru.python = python;
}
