let
  pkgsJSON = builtins.fromJSON (builtins.readFile ./nixpkgs.json);
  pkgsSrc = builtins.fetchTarball { inherit (pkgsJSON) url sha256; };
in
{ pkgs ? import pkgsSrc {}
}:

let
  pypi2nixJSON = builtins.fromJSON (builtins.readFile ./pypi2nix.json);
  configloaderJSON = builtins.fromJSON (builtins.readFile ./configloader.json);
  usersKeysJSON = builtins.fromJSON (builtins.readFile ./pubkeys.json);
  pypi2nixSrc = builtins.fetchTarball { inherit (pypi2nixJSON) url sha256; };
  configloaderSrc = builtins.fetchTarball { inherit (configloaderJSON) url sha256; };
  usersKeys = builtins.fetchTarball { inherit (usersKeysJSON) url sha256; };
  pypi2nix = import pypi2nixSrc { inherit pkgs; };
  configloader = import "${configloaderSrc}/nix" { inherit pkgs; };
  python = import ./requirements.nix { inherit pkgs; };
  version = builtins.replaceStrings ["\n"] [""]
    (builtins.readFile (toString ../version.txt));
  scriptWorkerConfig = pkgs.writeTextDir "scriptworker.yaml" (builtins.readFile ./configs/scriptworker.yaml);
  workerConfigs = ./configs;
  cmd = pkgs.writeScriptBin "shipitscript" ''
      #!${pkgs.bash}/bin/bash
      set -e
      mkdir -p -m 700 $CONFIGDIR
      # TaskCluster doesn't accept WORKER_ID longer than 22 chars
      export WORKER_ID=''${HOSTNAME:0:22}
      export TASK_SCRIPT_CONFIG="$CONFIGDIR/worker.json"
      $CONFIGLOADER $SCRIPTWORKER_CONFIG_TEMPLATE $CONFIGDIR/scriptworker.json
      $CONFIGLOADER $TASK_SCRIPT_CONFIG_TEMPLATE_DIR/$APP_CHANNEL/worker.json $TASK_SCRIPT_CONFIG
      $GIT_PATH config --global gpg.program $GPG_PATH
      $GIT_PATH clone https://github.com/mozilla-releng/cot-gpg-keys.git /app/gpg_key_repo
      echo $PUBLIC_KEY | base64 -d > /app/pubkey
      echo $PRIVATE_KEY | base64 -d > /app/privkey
      $(dirname $SCRIPTWORKER)/rebuild_gpg_homedirs $CONFIGDIR/scriptworker.json
      exec $SCRIPTWORKER $CONFIGDIR/scriptworker.json
    '';
    # TODO: should this be linked to a stable location, /check.sh?
    healthcheck = pkgs.writeScriptBin "healthcheck" ''
      #!${pkgs.bash}/bin/bash
      created=$(date -r /tmp/logs/worker.log +%s)
      now=$(date +%s)
      age=$[ $now - $created ]
      if [ $age -gt 180 ]; then
        echo "/tmp/logs/worker.log is too old: $created"
        exit 1
      fi
    '';

  self = python.mkDerivation rec {
    name = "shipitscript-${version}";
    src = builtins.filterSource pkgs.lib.cleanSourceFilter ../.;
    doCheck = false;
    buildInputs = builtins.attrValues python.packages;
    propagatedBuildInputs = with python.packages; [
      scriptworker
      shipitapi
    ];

    passthru = {
      inherit python;

      docker = pkgs.dockerTools.buildImage {
        runAsRoot = ''
          #!${pkgs.stdenv.shell}
          ${pkgs.dockerTools.shadowSetup}
          groupadd --gid 10001 app
          useradd --gid 10001 --uid 10001 --home-dir /app app
          mkdir -p --mode=1777 /tmp
          mkdir -p -m 700 /app
          chown app:app /app
          ln -s ${healthcheck}/bin/healthcheck /bin/healthcheck
        '';
        name = "shipitscript";
        tag = version;
        config = {
          User = "app";
          Cmd = [ "${cmd}/bin/shipitscript" ];
          Env = [
            "CONFIGDIR=/app/configs"
            "SSL_CERT_FILE=${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt"
            "CONFIGLOADER=${configloader}/bin/configloader"
            "SCRIPTWORKER=${python.packages.scriptworker}/bin/scriptworker"
            "SCRIPTWORKER_CONFIG_TEMPLATE=${scriptWorkerConfig}/scriptworker.yaml"
            "TASK_SCRIPT_CONFIG_TEMPLATE_DIR=${workerConfigs}"
            # The following env variables are used in the templates
            "TASK_SCRIPT=${self}/bin/shipitscript"
            "MARK_AS_SHIPPED_SCHEMA_FILE=${self}/lib/${python.interpreter.passthru.interpreter.libPrefix}/site-packages/shipitscript/data/mark_as_shipped_task_schema.json"
            "MARK_AS_STARTED_SCHEMA_FILE=${self}/lib/${python.interpreter.passthru.interpreter.libPrefix}/site-packages/shipitscript/data/mark_as_started_task_schema.json"
            "PUBKEYS=${usersKeys}/modules/scriptworker/files/git_pubkeys/"
            # Use custom gnupg without UI
            "GPG_PATH=${python.packages.gnupg20}/bin/gpg2"
            "GIT_PATH=${pkgs.git}/bin/git"
            # "GNUPGHOME=/app/.gnupg"
          ];
        };
        contents = [
          self
          pkgs.coreutils
          pkgs.bashInteractive
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
          -e setuptools-scm \
          -E gnupg20 \
          -E git
      '';

    };
  };

in self
