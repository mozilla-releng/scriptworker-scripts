# generated using pypi2nix tool (version: 2.0.0)
# See more at: https://github.com/garbas/pypi2nix
#
# COMMAND:
#   pypi2nix -V 3.7 -r ../requirements.txt -e flit -e intreehooks -e vcversioner -e pytest-runner -e setuptools-scm
#

{ pkgs ? import <nixpkgs> {},
  overrides ? ({ pkgs, python }: self: super: {})
}:

let

  inherit (pkgs) makeWrapper;
  inherit (pkgs.stdenv.lib) fix' extends inNixShell;

  pythonPackages =
  import "${toString pkgs.path}/pkgs/top-level/python-packages.nix" {
    inherit pkgs;
    inherit (pkgs) stdenv;
    python = pkgs.python37;
    # patching pip so it does not try to remove files when running nix-shell
    overrides =
      self: super: {
        bootstrapped-pip = super.bootstrapped-pip.overrideDerivation (old: {
          patchPhase = old.patchPhase + ''
            if [ -e $out/${pkgs.python37.sitePackages}/pip/req/req_install.py ]; then
              sed -i \
                -e "s|paths_to_remove.remove(auto_confirm)|#paths_to_remove.remove(auto_confirm)|"  \
                -e "s|self.uninstalled = paths_to_remove|#self.uninstalled = paths_to_remove|"  \
                $out/${pkgs.python37.sitePackages}/pip/req/req_install.py
            fi
          '';
        });
      };
  };

  commonBuildInputs = [];
  commonDoCheck = false;

  withPackages = pkgs':
    let
      pkgs = builtins.removeAttrs pkgs' ["__unfix__"];
      interpreterWithPackages = selectPkgsFn: pythonPackages.buildPythonPackage {
        name = "python37-interpreter";
        buildInputs = [ makeWrapper ] ++ (selectPkgsFn pkgs);
        buildCommand = ''
          mkdir -p $out/bin
          ln -s ${pythonPackages.python.interpreter} \
              $out/bin/${pythonPackages.python.executable}
          for dep in ${builtins.concatStringsSep " "
              (selectPkgsFn pkgs)}; do
            if [ -d "$dep/bin" ]; then
              for prog in "$dep/bin/"*; do
                if [ -x "$prog" ] && [ -f "$prog" ]; then
                  ln -s $prog $out/bin/`basename $prog`
                fi
              done
            fi
          done
          for prog in "$out/bin/"*; do
            wrapProgram "$prog" --prefix PYTHONPATH : "$PYTHONPATH"
          done
          pushd $out/bin
          ln -s ${pythonPackages.python.executable} python
          ln -s ${pythonPackages.python.executable} \
              python3
          popd
        '';
        passthru.interpreter = pythonPackages.python;
      };

      interpreter = interpreterWithPackages builtins.attrValues;
    in {
      __old = pythonPackages;
      inherit interpreter;
      inherit interpreterWithPackages;
      mkDerivation = pythonPackages.buildPythonPackage;
      packages = pkgs;
      overrideDerivation = drv: f:
        pythonPackages.buildPythonPackage (
          drv.drvAttrs // f drv.drvAttrs // { meta = drv.meta; }
        );
      withPackages = pkgs'':
        withPackages (pkgs // pkgs'');
    };

  python = withPackages {};

  generated = self: {
    "PyYAML" = python.mkDerivation {
      name = "PyYAML-3.13";
      src = pkgs.fetchurl {
        url = "https://files.pythonhosted.org/packages/9e/a3/1d13970c3f36777c583f136c136f804d70f500168edc1edea6daa7200769/PyYAML-3.13.tar.gz";
        sha256 = "3ef3092145e9b70e3ddd2c7ad59bdd0252a94dfe3949721633e41344de00a6bf";
      };
      doCheck = commonDoCheck;
      checkPhase = "";
      installCheckPhase = "";
      buildInputs = commonBuildInputs ++ [ ];
      propagatedBuildInputs = [ ];
      meta = with pkgs.stdenv.lib; {
        homepage = "http://pyyaml.org/wiki/PyYAML";
        license = licenses.mit;
        description = "YAML parser and emitter for Python";
      };
    };

    "aiohttp" = python.mkDerivation {
      name = "aiohttp-3.4.4";
      src = pkgs.fetchurl {
        url = "https://files.pythonhosted.org/packages/70/27/6098b4b60a3302a97f8ec97eb85d42f55a2fa904da4a369235a8e3b84352/aiohttp-3.4.4.tar.gz";
        sha256 = "51afec6ffa50a9da4cdef188971a802beb1ca8e8edb40fa429e5e529db3475fa";
      };
      doCheck = commonDoCheck;
      checkPhase = "";
      installCheckPhase = "";
      buildInputs = commonBuildInputs ++ [ ];
      propagatedBuildInputs = [
        self."async-timeout"
        self."attrs"
        self."chardet"
        self."multidict"
        self."yarl"
      ];
      meta = with pkgs.stdenv.lib; {
        homepage = "https://github.com/aio-libs/aiohttp";
        license = licenses.asl20;
        description = "Async http client/server framework (asyncio)";
      };
    };

    "arrow" = python.mkDerivation {
      name = "arrow-0.12.1";
      src = pkgs.fetchurl {
        url = "https://files.pythonhosted.org/packages/e0/86/4eb5228a43042e9a80fe8c84093a8a36f5db34a3767ebd5e1e7729864e7b/arrow-0.12.1.tar.gz";
        sha256 = "a558d3b7b6ce7ffc74206a86c147052de23d3d4ef0e17c210dd478c53575c4cd";
      };
      doCheck = commonDoCheck;
      checkPhase = "";
      installCheckPhase = "";
      buildInputs = commonBuildInputs ++ [ ];
      propagatedBuildInputs = [
        self."python-dateutil"
      ];
      meta = with pkgs.stdenv.lib; {
        homepage = "https://github.com/crsmithdev/arrow/";
        license = licenses.asl20;
        description = "Better dates and times for Python";
      };
    };

    "async-timeout" = python.mkDerivation {
      name = "async-timeout-3.0.1";
      src = pkgs.fetchurl {
        url = "https://files.pythonhosted.org/packages/a1/78/aae1545aba6e87e23ecab8d212b58bb70e72164b67eb090b81bb17ad38e3/async-timeout-3.0.1.tar.gz";
        sha256 = "0c3c816a028d47f659d6ff5c745cb2acf1f966da1fe5c19c77a70282b25f4c5f";
      };
      doCheck = commonDoCheck;
      checkPhase = "";
      installCheckPhase = "";
      buildInputs = commonBuildInputs ++ [ ];
      propagatedBuildInputs = [ ];
      meta = with pkgs.stdenv.lib; {
        homepage = "https://github.com/aio-libs/async_timeout/";
        license = licenses.asl20;
        description = "Timeout context manager for asyncio programs";
      };
    };

    "attrs" = python.mkDerivation {
      name = "attrs-18.2.0";
      src = pkgs.fetchurl {
        url = "https://files.pythonhosted.org/packages/0f/9e/26b1d194aab960063b266170e53c39f73ea0d0d3f5ce23313e0ec8ee9bdf/attrs-18.2.0.tar.gz";
        sha256 = "10cbf6e27dbce8c30807caf056c8eb50917e0eaafe86347671b57254006c3e69";
      };
      doCheck = commonDoCheck;
      checkPhase = "";
      installCheckPhase = "";
      buildInputs = commonBuildInputs ++ [ ];
      propagatedBuildInputs = [ ];
      meta = with pkgs.stdenv.lib; {
        homepage = "https://www.attrs.org/";
        license = licenses.mit;
        description = "Classes Without Boilerplate";
      };
    };

    "certifi" = python.mkDerivation {
      name = "certifi-2018.11.29";
      src = pkgs.fetchurl {
        url = "https://files.pythonhosted.org/packages/55/54/3ce77783acba5979ce16674fc98b1920d00b01d337cfaaf5db22543505ed/certifi-2018.11.29.tar.gz";
        sha256 = "47f9c83ef4c0c621eaef743f133f09fa8a74a9b75f037e8624f83bd1b6626cb7";
      };
      doCheck = commonDoCheck;
      checkPhase = "";
      installCheckPhase = "";
      buildInputs = commonBuildInputs ++ [ ];
      propagatedBuildInputs = [ ];
      meta = with pkgs.stdenv.lib; {
        homepage = "https://certifi.io/";
        license = licenses.mpl20;
        description = "Python package for providing Mozilla's CA Bundle.";
      };
    };

    "chardet" = python.mkDerivation {
      name = "chardet-3.0.4";
      src = pkgs.fetchurl {
        url = "https://files.pythonhosted.org/packages/fc/bb/a5768c230f9ddb03acc9ef3f0d4a3cf93462473795d18e9535498c8f929d/chardet-3.0.4.tar.gz";
        sha256 = "84ab92ed1c4d4f16916e05906b6b75a6c0fb5db821cc65e70cbd64a3e2a5eaae";
      };
      doCheck = commonDoCheck;
      checkPhase = "";
      installCheckPhase = "";
      buildInputs = commonBuildInputs ++ [ ];
      propagatedBuildInputs = [ ];
      meta = with pkgs.stdenv.lib; {
        homepage = "https://github.com/chardet/chardet";
        license = licenses.lgpl3;
        description = "Universal encoding detector for Python 2 and 3";
      };
    };

    "defusedxml" = python.mkDerivation {
      name = "defusedxml-0.5.0";
      src = pkgs.fetchurl {
        url = "https://files.pythonhosted.org/packages/74/ba/4ba4e89e21b5a2e267d80736ea674609a0a33cc4435a6d748ef04f1f9374/defusedxml-0.5.0.tar.gz";
        sha256 = "24d7f2f94f7f3cb6061acb215685e5125fbcdc40a857eff9de22518820b0a4f4";
      };
      doCheck = commonDoCheck;
      checkPhase = "";
      installCheckPhase = "";
      buildInputs = commonBuildInputs ++ [ ];
      propagatedBuildInputs = [ ];
      meta = with pkgs.stdenv.lib; {
        homepage = "https://github.com/tiran/defusedxml";
        license = "PSFL";
        description = "XML bomb protection for Python stdlib modules";
      };
    };

    "dictdiffer" = python.mkDerivation {
      name = "dictdiffer-0.7.1";
      src = pkgs.fetchurl {
        url = "https://files.pythonhosted.org/packages/b4/f4/d169c492d8daa2b91fc2c1bd98a12d379bef2f839d5989518571ec26a630/dictdiffer-0.7.1.tar.gz";
        sha256 = "e4f94167d037f70c11c6a8e7e289d81c8c7117bc02132cd82a0ab8fcba43cc08";
      };
      doCheck = commonDoCheck;
      checkPhase = "";
      installCheckPhase = "";
      buildInputs = commonBuildInputs ++ [
        self."pytest-runner"
      ];
      propagatedBuildInputs = [ ];
      meta = with pkgs.stdenv.lib; {
        homepage = "https://github.com/inveniosoftware/dictdiffer";
        license = "UNKNOWN";
        description = "Dictdiffer is a library that helps you to diff and patch dictionaries.";
      };
    };

    "docutils" = python.mkDerivation {
      name = "docutils-0.14";
      src = pkgs.fetchurl {
        url = "https://files.pythonhosted.org/packages/84/f4/5771e41fdf52aabebbadecc9381d11dea0fa34e4759b4071244fa094804c/docutils-0.14.tar.gz";
        sha256 = "51e64ef2ebfb29cae1faa133b3710143496eca21c530f3f71424d77687764274";
      };
      doCheck = commonDoCheck;
      checkPhase = "";
      installCheckPhase = "";
      buildInputs = commonBuildInputs ++ [ ];
      propagatedBuildInputs = [ ];
      meta = with pkgs.stdenv.lib; {
        homepage = "http://docutils.sourceforge.net/";
        license = "public domain, Python, 2-Clause BSD, GPL 3 (see COPYING.txt)";
        description = "Docutils -- Python Documentation Utilities";
      };
    };

    "flit" = python.mkDerivation {
      name = "flit-1.2.1";
      src = pkgs.fetchurl {
        url = "https://files.pythonhosted.org/packages/6a/55/a25505e3b3f5d804d1a0b6a64c582f4a264697c94862ccf71b8a1c62d16d/flit-1.2.1.tar.gz";
        sha256 = "6aefa6ff89a993af7a7af40d3df3d0387d6663df99797981ec41b1431ec6d1e1";
      };
      doCheck = commonDoCheck;
      checkPhase = "";
      installCheckPhase = "";
      buildInputs = commonBuildInputs ++ [ ];
      propagatedBuildInputs = [
        self."docutils"
        self."pytoml"
        self."requests"
      ];
      meta = with pkgs.stdenv.lib; {
        homepage = "https://github.com/takluyver/flit";
        license = "UNKNOWN";
        description = "A simple packaging tool for simple packages.";
      };
    };

    "frozendict" = python.mkDerivation {
      name = "frozendict-1.2";
      src = pkgs.fetchurl {
        url = "https://files.pythonhosted.org/packages/4e/55/a12ded2c426a4d2bee73f88304c9c08ebbdbadb82569ebdd6a0c007cfd08/frozendict-1.2.tar.gz";
        sha256 = "774179f22db2ef8a106e9c38d4d1f8503864603db08de2e33be5b778230f6e45";
      };
      doCheck = commonDoCheck;
      checkPhase = "";
      installCheckPhase = "";
      buildInputs = commonBuildInputs ++ [ ];
      propagatedBuildInputs = [ ];
      meta = with pkgs.stdenv.lib; {
        homepage = "https://github.com/slezica/python-frozendict";
        license = licenses.mit;
        description = "An immutable dictionary";
      };
    };

    "idna" = python.mkDerivation {
      name = "idna-2.7";
      src = pkgs.fetchurl {
        url = "https://files.pythonhosted.org/packages/65/c4/80f97e9c9628f3cac9b98bfca0402ede54e0563b56482e3e6e45c43c4935/idna-2.7.tar.gz";
        sha256 = "684a38a6f903c1d71d6d5fac066b58d7768af4de2b832e426ec79c30daa94a16";
      };
      doCheck = commonDoCheck;
      checkPhase = "";
      installCheckPhase = "";
      buildInputs = commonBuildInputs ++ [ ];
      propagatedBuildInputs = [ ];
      meta = with pkgs.stdenv.lib; {
        homepage = "https://github.com/kjd/idna";
        license = licenses.bsdOriginal;
        description = "Internationalized Domain Names in Applications (IDNA)";
      };
    };

    "intreehooks" = python.mkDerivation {
      name = "intreehooks-1.0";
      src = pkgs.fetchurl {
        url = "https://files.pythonhosted.org/packages/f9/a5/5dacebf93232a847970921af2b020f9f2a8e0064e3a97727cd38efc77ba0/intreehooks-1.0.tar.gz";
        sha256 = "87e600d3b16b97ed219c078681260639e77ef5a17c0e0dbdd5a302f99b4e34e1";
      };
      doCheck = commonDoCheck;
      checkPhase = "";
      installCheckPhase = "";
      buildInputs = commonBuildInputs ++ [ ];
      propagatedBuildInputs = [
        self."pytoml"
      ];
      meta = with pkgs.stdenv.lib; {
        homepage = "https://github.com/takluyver/intreehooks";
        license = "UNKNOWN";
        description = "Load a PEP 517 backend from inside the source tree";
      };
    };

    "json-e" = python.mkDerivation {
      name = "json-e-3.0.0";
      src = pkgs.fetchurl {
        url = "https://files.pythonhosted.org/packages/98/37/efe9813b85989e716f8cde7ab716f17ff98e1e18f68666d522eadd4680a8/json-e-3.0.0.tar.gz";
        sha256 = "d2914f785d93ecc4f0b2ad6e3f2791f33327eaa740a3c4917d68a9a485dd282d";
      };
      doCheck = commonDoCheck;
      checkPhase = "";
      installCheckPhase = "";
      buildInputs = commonBuildInputs ++ [ ];
      propagatedBuildInputs = [ ];
      meta = with pkgs.stdenv.lib; {
        homepage = "https://taskcluster.github.io/json-e/";
        license = licenses.mpl20;
        description = "A data-structure parameterization system written for embedding context in JSON objects";
      };
    };

    "jsonschema" = python.mkDerivation {
      name = "jsonschema-2.6.0";
      src = pkgs.fetchurl {
        url = "https://files.pythonhosted.org/packages/58/b9/171dbb07e18c6346090a37f03c7e74410a1a56123f847efed59af260a298/jsonschema-2.6.0.tar.gz";
        sha256 = "6ff5f3180870836cae40f06fa10419f557208175f13ad7bc26caa77beb1f6e02";
      };
      doCheck = commonDoCheck;
      checkPhase = "";
      installCheckPhase = "";
      buildInputs = commonBuildInputs ++ [
        self."vcversioner"
      ];
      propagatedBuildInputs = [ ];
      meta = with pkgs.stdenv.lib; {
        homepage = "http://github.com/Julian/jsonschema";
        license = licenses.mit;
        description = "An implementation of JSON Schema validation for Python";
      };
    };

    "mohawk" = python.mkDerivation {
      name = "mohawk-0.3.4";
      src = pkgs.fetchurl {
        url = "https://files.pythonhosted.org/packages/19/22/10f696548a8d41ad41b92ab6c848c60c669e18c8681c179265ce4d048b03/mohawk-0.3.4.tar.gz";
        sha256 = "e98b331d9fa9ece7b8be26094cbe2d57613ae882133cc755167268a984bc0ab3";
      };
      doCheck = commonDoCheck;
      checkPhase = "";
      installCheckPhase = "";
      buildInputs = commonBuildInputs ++ [ ];
      propagatedBuildInputs = [
        self."six"
      ];
      meta = with pkgs.stdenv.lib; {
        homepage = "https://github.com/kumar303/mohawk";
        license = licenses.mpl20;
        description = "Library for Hawk HTTP authorization";
      };
    };

    "multidict" = python.mkDerivation {
      name = "multidict-4.5.2";
      src = pkgs.fetchurl {
        url = "https://files.pythonhosted.org/packages/7f/8f/b3c8c5b062309e854ce5b726fc101195fbaa881d306ffa5c2ba19efa3af2/multidict-4.5.2.tar.gz";
        sha256 = "024b8129695a952ebd93373e45b5d341dbb87c17ce49637b34000093f243dd4f";
      };
      doCheck = commonDoCheck;
      checkPhase = "";
      installCheckPhase = "";
      buildInputs = commonBuildInputs ++ [ ];
      propagatedBuildInputs = [ ];
      meta = with pkgs.stdenv.lib; {
        homepage = "https://github.com/aio-libs/multidict";
        license = licenses.asl20;
        description = "multidict implementation";
      };
    };

    "pexpect" = python.mkDerivation {
      name = "pexpect-4.6.0";
      src = pkgs.fetchurl {
        url = "https://files.pythonhosted.org/packages/89/43/07d07654ee3e25235d8cea4164cdee0ec39d1fda8e9203156ebe403ffda4/pexpect-4.6.0.tar.gz";
        sha256 = "2a8e88259839571d1251d278476f3eec5db26deb73a70be5ed5dc5435e418aba";
      };
      doCheck = commonDoCheck;
      checkPhase = "";
      installCheckPhase = "";
      buildInputs = commonBuildInputs ++ [ ];
      propagatedBuildInputs = [
        self."ptyprocess"
      ];
      meta = with pkgs.stdenv.lib; {
        homepage = "https://pexpect.readthedocs.io/";
        license = "ISC license";
        description = "Pexpect allows easy control of interactive console applications.";
      };
    };

    "ptyprocess" = python.mkDerivation {
      name = "ptyprocess-0.6.0";
      src = pkgs.fetchurl {
        url = "https://files.pythonhosted.org/packages/7d/2d/e4b8733cf79b7309d84c9081a4ab558c89d8c89da5961bf4ddb050ca1ce0/ptyprocess-0.6.0.tar.gz";
        sha256 = "923f299cc5ad920c68f2bc0bc98b75b9f838b93b599941a6b63ddbc2476394c0";
      };
      doCheck = commonDoCheck;
      checkPhase = "";
      installCheckPhase = "";
      buildInputs = commonBuildInputs ++ [ ];
      propagatedBuildInputs = [ ];
      meta = with pkgs.stdenv.lib; {
        homepage = "https://github.com/pexpect/ptyprocess";
        license = "UNKNOWN";
        description = "Run a subprocess in a pseudo terminal";
      };
    };

    "pytest-runner" = python.mkDerivation {
      name = "pytest-runner-4.2";
      src = pkgs.fetchurl {
        url = "https://files.pythonhosted.org/packages/9e/b7/fe6e8f87f9a756fd06722216f1b6698ccba4d269eac6329d9f0c441d0f93/pytest-runner-4.2.tar.gz";
        sha256 = "d23f117be39919f00dd91bffeb4f15e031ec797501b717a245e377aee0f577be";
      };
      doCheck = commonDoCheck;
      checkPhase = "";
      installCheckPhase = "";
      buildInputs = commonBuildInputs ++ [
        self."setuptools-scm"
      ];
      propagatedBuildInputs = [ ];
      meta = with pkgs.stdenv.lib; {
        homepage = "https://github.com/pytest-dev/pytest-runner";
        license = "UNKNOWN";
        description = "Invoke py.test as distutils command with dependency resolution";
      };
    };

    "python-dateutil" = python.mkDerivation {
      name = "python-dateutil-2.7.5";
      src = pkgs.fetchurl {
        url = "https://files.pythonhosted.org/packages/0e/01/68747933e8d12263d41ce08119620d9a7e5eb72c876a3442257f74490da0/python-dateutil-2.7.5.tar.gz";
        sha256 = "88f9287c0174266bb0d8cedd395cfba9c58e87e5ad86b2ce58859bc11be3cf02";
      };
      doCheck = commonDoCheck;
      checkPhase = "";
      installCheckPhase = "";
      buildInputs = commonBuildInputs ++ [ ];
      propagatedBuildInputs = [
        self."six"
      ];
      meta = with pkgs.stdenv.lib; {
        homepage = "https://dateutil.readthedocs.io";
        license = "Dual License";
        description = "Extensions to the standard Python datetime module";
      };
    };

    "python-gnupg" = python.mkDerivation {
      name = "python-gnupg-0.4.3";
      src = pkgs.fetchurl {
        url = "https://files.pythonhosted.org/packages/fd/a6/4ae8ec46a256444f65d745a92827c05fe6d4f3f4e1a40289a58ac37fe2b9/python-gnupg-0.4.3.tar.gz";
        sha256 = "2d158dfc6b54927752b945ebe57e6a0c45da27747fa3b9ae66eccc0d2147ac0d";
      };
      doCheck = commonDoCheck;
      checkPhase = "";
      installCheckPhase = "";
      buildInputs = commonBuildInputs ++ [ ];
      propagatedBuildInputs = [ ];
      meta = with pkgs.stdenv.lib; {
        homepage = "http://gnupg.readthedocs.io/en/latest/";
        license = "Copyright (C) 2008-2018 by Vinay Sajip. All Rights Reserved. See LICENSE.txt for license.";
        description = "A wrapper for the Gnu Privacy Guard (GPG or GnuPG)";
      };
    };

    "pytoml" = python.mkDerivation {
      name = "pytoml-0.1.20";
      src = pkgs.fetchurl {
        url = "https://files.pythonhosted.org/packages/35/35/da1123673c54b6d701453fcd20f751d6a1fae43339b3993ae458875576e4/pytoml-0.1.20.tar.gz";
        sha256 = "ca2d0cb127c938b8b76a9a0d0f855cf930c1d50cc3a0af6d3595b566519a1013";
      };
      doCheck = commonDoCheck;
      checkPhase = "";
      installCheckPhase = "";
      buildInputs = commonBuildInputs ++ [ ];
      propagatedBuildInputs = [ ];
      meta = with pkgs.stdenv.lib; {
        homepage = "https://github.com/avakar/pytoml";
        license = licenses.mit;
        description = "A parser for TOML-0.4.0";
      };
    };

    "redo" = python.mkDerivation {
      name = "redo-2.0.2";
      src = pkgs.fetchurl {
        url = "https://files.pythonhosted.org/packages/02/61/a23bb9e8ef2047f205f2005cb6ef34f6f9991eb9a4125cc1a9623b315928/redo-2.0.2.tar.gz";
        sha256 = "703603d61b4ae7fa14a9dce3db22d8789284e99be997f558137612e847ead3cb";
      };
      doCheck = commonDoCheck;
      checkPhase = "";
      installCheckPhase = "";
      buildInputs = commonBuildInputs ++ [ ];
      propagatedBuildInputs = [ ];
      meta = with pkgs.stdenv.lib; {
        homepage = "https://github.com/bhearsum/redo";
        license = "UNKNOWN";
        description = "Utilities to retry Python callables.";
      };
    };

    "requests" = python.mkDerivation {
      name = "requests-2.20.1";
      src = pkgs.fetchurl {
        url = "https://files.pythonhosted.org/packages/40/35/298c36d839547b50822985a2cf0611b3b978a5ab7a5af5562b8ebe3e1369/requests-2.20.1.tar.gz";
        sha256 = "ea881206e59f41dbd0bd445437d792e43906703fff75ca8ff43ccdb11f33f263";
      };
      doCheck = commonDoCheck;
      checkPhase = "";
      installCheckPhase = "";
      buildInputs = commonBuildInputs ++ [ ];
      propagatedBuildInputs = [
        self."certifi"
        self."chardet"
        self."idna"
        self."urllib3"
      ];
      meta = with pkgs.stdenv.lib; {
        homepage = "http://python-requests.org";
        license = licenses.asl20;
        description = "Python HTTP for Humans.";
      };
    };

    "scriptworker" = python.mkDerivation {
      name = "scriptworker-17.0.1";
      src = pkgs.fetchurl {
        url = "https://files.pythonhosted.org/packages/e5/79/2c4b8534b0ff004c8f591d0d69da9334c692ee2e13d1e378dcdbef662721/scriptworker-17.0.1.tar.gz";
        sha256 = "471acdadaa8796a1a348929303cecdeb11647bf701b5fa9823a88ab982b1042b";
      };
      doCheck = commonDoCheck;
      checkPhase = "";
      installCheckPhase = "";
      buildInputs = commonBuildInputs ++ [ ];
      propagatedBuildInputs = [
        self."PyYAML"
        self."aiohttp"
        self."arrow"
        self."defusedxml"
        self."dictdiffer"
        self."frozendict"
        self."json-e"
        self."jsonschema"
        self."pexpect"
        self."python-gnupg"
        self."taskcluster"
        self."virtualenv"
      ];
      meta = with pkgs.stdenv.lib; {
        homepage = "https://github.com/mozilla-releng/scriptworker";
        license = licenses.mpl20;
        description = "TaskCluster Script Worker";
      };
    };

    "setuptools-scm" = python.mkDerivation {
      name = "setuptools-scm-3.1.0";
      src = pkgs.fetchurl {
        url = "https://files.pythonhosted.org/packages/09/b4/d148a70543b42ff3d81d57381f33104f32b91f970ad7873f463e75bf7453/setuptools_scm-3.1.0.tar.gz";
        sha256 = "1191f2a136b5e86f7ca8ab00a97ef7aef997131f1f6d4971be69a1ef387d8b40";
      };
      doCheck = commonDoCheck;
      checkPhase = "";
      installCheckPhase = "";
      buildInputs = commonBuildInputs ++ [ ];
      propagatedBuildInputs = [ ];
      meta = with pkgs.stdenv.lib; {
        homepage = "https://github.com/pypa/setuptools_scm/";
        license = licenses.mit;
        description = "the blessed package to manage your versions by scm tags";
      };
    };

    "shipitapi" = python.mkDerivation {
      name = "shipitapi-2.0.0";
      src = pkgs.fetchurl {
        url = "https://files.pythonhosted.org/packages/6f/90/10206e1497b17352577c68aeaed91b752e9fa6fef66c0699a277e4a670f6/shipitapi-2.0.0.tar.gz";
        sha256 = "c335cc97a1ec7e6eb653e1e2d2f026258916e245b811f9363d3cd4755b740494";
      };
      doCheck = commonDoCheck;
      checkPhase = "";
      installCheckPhase = "";
      buildInputs = commonBuildInputs ++ [ ];
      propagatedBuildInputs = [
        self."certifi"
        self."mohawk"
        self."redo"
        self."requests"
      ];
      meta = with pkgs.stdenv.lib; {
        homepage = "https://github.com/MihaiTabara/shipitapi";
        license = "MPL";
        description = "Lib package to facilitate access to Ship IT API operations";
      };
    };

    "six" = python.mkDerivation {
      name = "six-1.11.0";
      src = pkgs.fetchurl {
        url = "https://files.pythonhosted.org/packages/16/d8/bc6316cf98419719bd59c91742194c111b6f2e85abac88e496adefaf7afe/six-1.11.0.tar.gz";
        sha256 = "70e8a77beed4562e7f14fe23a786b54f6296e34344c23bc42f07b15018ff98e9";
      };
      doCheck = commonDoCheck;
      checkPhase = "";
      installCheckPhase = "";
      buildInputs = commonBuildInputs ++ [ ];
      propagatedBuildInputs = [ ];
      meta = with pkgs.stdenv.lib; {
        homepage = "http://pypi.python.org/pypi/six/";
        license = licenses.mit;
        description = "Python 2 and 3 compatibility utilities";
      };
    };

    "slugid" = python.mkDerivation {
      name = "slugid-1.0.7";
      src = pkgs.fetchurl {
        url = "https://files.pythonhosted.org/packages/dd/96/b05c6d357f8d6932bea2b360537360517d1154b82cc71b8eccb70b28bdde/slugid-1.0.7.tar.gz";
        sha256 = "6dab3c7eef0bb423fb54cb7752e0f466ddd0ee495b78b763be60e8a27f69e779";
      };
      doCheck = commonDoCheck;
      checkPhase = "";
      installCheckPhase = "";
      buildInputs = commonBuildInputs ++ [ ];
      propagatedBuildInputs = [ ];
      meta = with pkgs.stdenv.lib; {
        homepage = "http://taskcluster.github.io/slugid.py";
        license = licenses.mpl20;
        description = "Base64 encoded uuid v4 slugs";
      };
    };

    "taskcluster" = python.mkDerivation {
      name = "taskcluster-6.0.0";
      src = pkgs.fetchurl {
        url = "https://files.pythonhosted.org/packages/06/6a/66bf42549bb69618159b0515c3001b9b8c21bbb5b28f16fcb14cfeef3318/taskcluster-6.0.0.tar.gz";
        sha256 = "48ecd4898c7928deddfb34cb1cfe2b2505c68416e6c503f8a7f3dd0572425e96";
      };
      doCheck = commonDoCheck;
      checkPhase = "";
      installCheckPhase = "";
      buildInputs = commonBuildInputs ++ [ ];
      propagatedBuildInputs = [
        self."aiohttp"
        self."async-timeout"
        self."mohawk"
        self."requests"
        self."six"
        self."slugid"
        self."taskcluster-urls"
      ];
      meta = with pkgs.stdenv.lib; {
        homepage = "https://github.com/taskcluster/taskcluster-client.py";
        license = "UNKNOWN";
        description = "Python client for Taskcluster";
      };
    };

    "taskcluster-urls" = python.mkDerivation {
      name = "taskcluster-urls-11.0.0";
      src = pkgs.fetchurl {
        url = "https://files.pythonhosted.org/packages/69/c1/1f0efd104c7bd6dbb42a7d0c7f1f5f4be05c108e873add8f466e6de9f387/taskcluster-urls-11.0.0.tar.gz";
        sha256 = "18dcaa9c2412d34ff6c78faca33f0dd8f2384e3f00a98d5832c62d6d664741f0";
      };
      doCheck = commonDoCheck;
      checkPhase = "";
      installCheckPhase = "";
      buildInputs = commonBuildInputs ++ [ ];
      propagatedBuildInputs = [ ];
      meta = with pkgs.stdenv.lib; {
        homepage = "https://github.com/taskcluster/taskcluster-lib-urls";
        license = licenses.mpl20;
        description = "Standardized url generator for taskcluster resources.";
      };
    };

    "urllib3" = python.mkDerivation {
      name = "urllib3-1.24.1";
      src = pkgs.fetchurl {
        url = "https://files.pythonhosted.org/packages/b1/53/37d82ab391393565f2f831b8eedbffd57db5a718216f82f1a8b4d381a1c1/urllib3-1.24.1.tar.gz";
        sha256 = "de9529817c93f27c8ccbfead6985011db27bd0ddfcdb2d86f3f663385c6a9c22";
      };
      doCheck = commonDoCheck;
      checkPhase = "";
      installCheckPhase = "";
      buildInputs = commonBuildInputs ++ [ ];
      propagatedBuildInputs = [
        self."certifi"
        self."idna"
      ];
      meta = with pkgs.stdenv.lib; {
        homepage = "https://urllib3.readthedocs.io/";
        license = licenses.mit;
        description = "HTTP library with thread-safe connection pooling, file post, and more.";
      };
    };

    "vcversioner" = python.mkDerivation {
      name = "vcversioner-2.16.0.0";
      src = pkgs.fetchurl {
        url = "https://files.pythonhosted.org/packages/c5/cc/33162c0a7b28a4d8c83da07bc2b12cee58c120b4a9e8bba31c41c8d35a16/vcversioner-2.16.0.0.tar.gz";
        sha256 = "dae60c17a479781f44a4010701833f1829140b1eeccd258762a74974aa06e19b";
      };
      doCheck = commonDoCheck;
      checkPhase = "";
      installCheckPhase = "";
      buildInputs = commonBuildInputs ++ [ ];
      propagatedBuildInputs = [ ];
      meta = with pkgs.stdenv.lib; {
        homepage = "https://github.com/habnabit/vcversioner";
        license = "ISC";
        description = "Use version control tags to discover version numbers";
      };
    };

    "virtualenv" = python.mkDerivation {
      name = "virtualenv-16.1.0";
      src = pkgs.fetchurl {
        url = "https://files.pythonhosted.org/packages/4e/8b/75469c270ac544265f0020aa7c4ea925c5284b23e445cf3aa8b99f662690/virtualenv-16.1.0.tar.gz";
        sha256 = "f899fafcd92e1150f40c8215328be38ff24b519cd95357fa6e78e006c7638208";
      };
      doCheck = commonDoCheck;
      checkPhase = "";
      installCheckPhase = "";
      buildInputs = commonBuildInputs ++ [ ];
      propagatedBuildInputs = [ ];
      meta = with pkgs.stdenv.lib; {
        homepage = "https://virtualenv.pypa.io/";
        license = licenses.mit;
        description = "Virtual Python Environment builder";
      };
    };

    "yarl" = python.mkDerivation {
      name = "yarl-1.2.6";
      src = pkgs.fetchurl {
        url = "https://files.pythonhosted.org/packages/43/b8/057c3e5b546ff4b24263164ecda13f6962d85c9dc477fcc0bcdcb3adb658/yarl-1.2.6.tar.gz";
        sha256 = "c8cbc21bbfa1dd7d5386d48cc814fe3d35b80f60299cdde9279046f399c3b0d8";
      };
      doCheck = commonDoCheck;
      checkPhase = "";
      installCheckPhase = "";
      buildInputs = commonBuildInputs ++ [ ];
      propagatedBuildInputs = [
        self."idna"
        self."multidict"
      ];
      meta = with pkgs.stdenv.lib; {
        homepage = "https://github.com/aio-libs/yarl/";
        license = licenses.asl20;
        description = "Yet another URL library";
      };
    };
  };
  localOverridesFile = ./requirements_override.nix;
  localOverrides = import localOverridesFile { inherit pkgs python; };
  commonOverrides = [
    
  ];
  paramOverrides = [
    (overrides { inherit pkgs python; })
  ];
  allOverrides =
    (if (builtins.pathExists localOverridesFile)
     then [localOverrides] else [] ) ++ commonOverrides ++ paramOverrides;

in python.withPackages
   (fix' (pkgs.lib.fold
            extends
            generated
            allOverrides
         )
   )