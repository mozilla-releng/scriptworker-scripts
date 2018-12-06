{ pkgs, python }:

self: super: {

  "python-dateutil" = python.overrideDerivation super."python-dateutil" (old: {
    buildInputs = old.buildInputs ++ [ self."setuptools-scm" ];
  });
}
