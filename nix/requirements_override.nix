{ pkgs, python }:

self: super: {

  "python-dateutil" = python.overrideDerivation super."python-dateutil" (old: {
    buildInputs = old.buildInputs ++ [ self."setuptools-scm" ];
  });

  "taskcluster" = python.overrideDerivation super."taskcluster" (old: {
    patchPhase = ''
      sed -i \
        -e "s|'mohawk>=0.3.4,<0.4',|'mohawk',|" \
        setup.py
    '';
  });

}
