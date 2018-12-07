{ pkgs ? import <nixpkgs> {} }:

let

  python = import ./requirements.nix { inherit pkgs; };
  version = builtins.replaceStrings ["\n"] [""]
    (builtins.readFile (toString ../version.txt));
  pypi2nix = import (pkgs.fetchFromGitHub (builtins.fromJSON (builtins.readFile ./pypi2nix.json))) { inherit pkgs; };

  self = python.mkDerivation rec {
    name = "shipitsript-${version}";
    src = builtins.filterSource
      (path: type: baseNameOf path != ".git"
                && baseNameOf path != "result"
                ) ../.;
    doCheck = false;
    buildInputs = builtins.attrValues python.packages;
    propagatedBuildInputs = with python.packages; [
      scriptworker
      shipitapi
    ];

    passthru = {

      docker = pkgs.dockerTools.buildImage {
        name = "shipitsript";
        tag = version;
        contents = [
          self
        ];
      };

      # to update the dependencies run the following 2 commands:
      # nix-build -A update
      # ./result
      update = pkgs.writeScript "update-${self.name}" ''
        pushd ${toString ./.}
        ${pypi2nix}/bin/pypi2nix \
          -V 3.7 \
          -r ../requirements.txt \
          -e flit \
          -e intreehooks \
          -e vcversioner \
          -e pytest-runner \
          -e setuptools-scm
      '';

      tarball =
        let
          closureInfo = pkgs.closureInfo { rootPaths = [ self ]; };
        in
          pkgs.runCommand "${self.name}.nix.tar.gz" {} ''
            mkdir -p nix/store bin
            # TODO: add some metadata?
            for d in $(cat ${closureInfo}/store-paths); do
              cp -a $d nix/store
            done
            ln -s ${self}/bin/shipitscript bin/
            tar -czf $out --exclude=.attr-0 --exclude=env-vars .
          '';

    };

  };

in self
