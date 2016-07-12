# generated using pypi2nix tool (version: 1.2.0)
#
# COMMAND:
#   pypi2nix -r requirements-nix.txt -V 3.5
#

{ pkgs, python, commonBuildInputs ? [], commonDoCheck ? false }:

self: {

  "aiohttp" = python.mkDerivation {
    name = "aiohttp-0.22.0a0";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/88/10/ba7c03e3cb827efa05cb57e3969a1de002d61497b5941f691af970f07c48/aiohttp-0.22.0a0.tar.gz";
      sha256= "5c6f1d5d62117d6962cf046a6490fa7798a2939629bf289694d3178ce6c03349";
    };
    doCheck = commonDoCheck;
    buildInputs = commonBuildInputs;
    propagatedBuildInputs = [
      self."chardet"
      self."multidict"
    ];
    meta = with pkgs.stdenv.lib; {
      homepage = "";
      license = "Apache 2";
      description = "http client/server for asyncio";
    };
    passthru.top_level = false;
  };



  "arrow" = python.mkDerivation {
    name = "arrow-0.8.0";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/58/91/21d65af4899adbcb4158c8f0def8ce1a6d18ddcd8bbb3f5a3800f03b9308/arrow-0.8.0.tar.gz";
      sha256= "b210c17d6bb850011700b9f54c1ca0eaf8cbbd441f156f0cd292e1fbda84e7af";
    };
    doCheck = commonDoCheck;
    buildInputs = commonBuildInputs;
    propagatedBuildInputs = [
      self."python-dateutil"
    ];
    meta = with pkgs.stdenv.lib; {
      homepage = "";
      license = licenses.asl20;
      description = "Better dates and times for Python";
    };
    passthru.top_level = false;
  };



  "chardet" = python.mkDerivation {
    name = "chardet-2.3.0";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/7d/87/4e3a3f38b2f5c578ce44f8dc2aa053217de9f0b6d737739b0ddac38ed237/chardet-2.3.0.tar.gz";
      sha256= "e53e38b3a4afe6d1132de62b7400a4ac363452dc5dfcf8d88e8e0cce663c68aa";
    };
    doCheck = commonDoCheck;
    buildInputs = commonBuildInputs;
    propagatedBuildInputs = [ ];
    meta = with pkgs.stdenv.lib; {
      homepage = "";
      license = "LGPL";
      description = "Universal encoding detector for Python 2 and 3";
    };
    passthru.top_level = false;
  };



  "coverage" = python.mkDerivation {
    name = "coverage-4.1";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/2d/10/6136c8e10644c16906edf4d9f7c782c0f2e7ed47ff2f41f067384e432088/coverage-4.1.tar.gz";
      sha256= "41632b5e2c0ec510e4c0f1f0f02a702477d1f837693964390553539217c92b07";
    };
    doCheck = commonDoCheck;
    buildInputs = commonBuildInputs;
    propagatedBuildInputs = [ ];
    meta = with pkgs.stdenv.lib; {
      homepage = "";
      license = licenses.asl20;
      description = "Code coverage measurement for Python";
    };
    passthru.top_level = false;
  };



  "defusedxml" = python.mkDerivation {
    name = "defusedxml-0.4.1";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/09/3b/b1afa9649f48517d027e99413fec54f387f648c90156b3cf6451c8cd45f9/defusedxml-0.4.1.tar.gz";
      sha256= "cd551d5a518b745407635bb85116eb813818ecaf182e773c35b36239fc3f2478";
    };
    doCheck = commonDoCheck;
    buildInputs = commonBuildInputs;
    propagatedBuildInputs = [ ];
    meta = with pkgs.stdenv.lib; {
      homepage = "";
      license = "PSFL";
      description = "XML bomb protection for Python stdlib modules";
    };
    passthru.top_level = false;
  };



  "ecdsa" = python.mkDerivation {
    name = "ecdsa-0.13";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/f9/e5/99ebb176e47f150ac115ffeda5fedb6a3dbb3c00c74a59fd84ddf12f5857/ecdsa-0.13.tar.gz";
      sha256= "64cf1ee26d1cde3c73c6d7d107f835fed7c6a2904aef9eac223d57ad800c43fa";
    };
    doCheck = commonDoCheck;
    buildInputs = commonBuildInputs;
    propagatedBuildInputs = [ ];
    meta = with pkgs.stdenv.lib; {
      homepage = "";
      license = licenses.mit;
      description = "ECDSA cryptographic signature library (pure python)";
    };
    passthru.top_level = false;
  };



  "flake8" = python.mkDerivation {
    name = "flake8-2.6.2";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/53/0a/b2c28a77dfc508ed9f7334252311e1aaf8f0ceaaeb1a8f15fa4ba3e2d847/flake8-2.6.2.tar.gz";
      sha256= "231cd86194aaec4bdfaa553ae1a1cd9b7b4558332fbc10136c044940d587a778";
    };
    doCheck = commonDoCheck;
    buildInputs = commonBuildInputs;
    propagatedBuildInputs = [
      self."mccabe"
      self."pycodestyle"
      self."pyflakes"
    ];
    meta = with pkgs.stdenv.lib; {
      homepage = "";
      license = licenses.mit;
      description = "the modular source code checker: pep8, pyflakes and co";
    };
    passthru.top_level = false;
  };



  "frozendict" = python.mkDerivation {
    name = "frozendict-0.6";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/ad/15/464e126260c0dd9ade67df7ec3ad8a75e23c51bb5bb604d48e274cfc9b19/frozendict-0.6.tar.gz";
      sha256= "168791393c2c642264a6839aac5e7c6a34b3a284aa02b8c950739962f756163c";
    };
    doCheck = commonDoCheck;
    buildInputs = commonBuildInputs;
    propagatedBuildInputs = [ ];
    meta = with pkgs.stdenv.lib; {
      homepage = "";
      license = licenses.mit;
      description = "An immutable dictionary";
    };
    passthru.top_level = false;
  };



  "future" = python.mkDerivation {
    name = "future-0.15.2";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/5a/f4/99abde815842bc6e97d5a7806ad51236630da14ca2f3b1fce94c0bb94d3d/future-0.15.2.tar.gz";
      sha256= "3d3b193f20ca62ba7d8782589922878820d0a023b885882deec830adbf639b97";
    };
    doCheck = commonDoCheck;
    buildInputs = commonBuildInputs;
    propagatedBuildInputs = [ ];
    meta = with pkgs.stdenv.lib; {
      homepage = "";
      license = licenses.mit;
      description = "Clean single-source support for Python 3 and 2";
    };
    passthru.top_level = false;
  };



  "jsonschema" = python.mkDerivation {
    name = "jsonschema-2.5.1";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/58/0d/c816f5ea5adaf1293a1d81d32e4cdfdaf8496973aa5049786d7fdb14e7e7/jsonschema-2.5.1.tar.gz";
      sha256= "36673ac378feed3daa5956276a829699056523d7961027911f064b52255ead41";
    };
    doCheck = commonDoCheck;
    buildInputs = commonBuildInputs;
    propagatedBuildInputs = [ ];
    meta = with pkgs.stdenv.lib; {
      homepage = "";
      license = licenses.mit;
      description = "An implementation of JSON Schema validation for Python";
    };
    passthru.top_level = false;
  };



  "mccabe" = python.mkDerivation {
    name = "mccabe-0.5.0";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/57/fa/4a0cda4cf9877d2bd12ab031ae4ecfdc5c1bbb6e68f3fe80da4f29947c2a/mccabe-0.5.0.tar.gz";
      sha256= "379358498f58f69157b53f59f46aefda0e9a3eb81365238f69fbedf7014e21ab";
    };
    doCheck = commonDoCheck;
    buildInputs = commonBuildInputs;
    propagatedBuildInputs = [ ];
    meta = with pkgs.stdenv.lib; {
      homepage = "";
      license = "Expat license";
      description = "McCabe checker, plugin for flake8";
    };
    passthru.top_level = false;
  };



  "mohawk" = python.mkDerivation {
    name = "mohawk-0.3.2.1";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/4e/1a/33a5a96fe29d3ae38be45d7cb02d9340bd9cb5fdf924e91b39cf2c87b8ed/mohawk-0.3.2.1.tar.gz";
      sha256= "46e98d8349f927b40227f1a9f0021509fedcf0398e1feb22dac954010f625f1d";
    };
    doCheck = commonDoCheck;
    buildInputs = commonBuildInputs;
    propagatedBuildInputs = [
      self."six"
    ];
    meta = with pkgs.stdenv.lib; {
      homepage = "";
      license = "MPL 2.0 (Mozilla Public License)";
      description = "Library for Hawk HTTP authorization";
    };
    passthru.top_level = false;
  };



  "multidict" = python.mkDerivation {
    name = "multidict-1.1.0";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/74/2e/1cc4df5eeb33fa8b8ecbb81c27861aa7eb624d781fe3ff3ea3c4fb703cfe/multidict-1.1.0.tar.gz";
      sha256= "2f33750b9d0df41c83bc6a46931d218f0d0bad4d7799e6877be8ad33bdc64c19";
    };
    doCheck = commonDoCheck;
    buildInputs = commonBuildInputs;
    propagatedBuildInputs = [ ];
    meta = with pkgs.stdenv.lib; {
      homepage = "";
      license = "Apache 2";
      description = "multidict implementation";
    };
    passthru.top_level = false;
  };



  "py" = python.mkDerivation {
    name = "py-1.4.31";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/f4/9a/8dfda23f36600dd701c6722316ba8a3ab4b990261f83e7d3ffc6dfedf7ef/py-1.4.31.tar.gz";
      sha256= "a6501963c725fc2554dabfece8ae9a8fb5e149c0ac0a42fd2b02c5c1c57fc114";
    };
    doCheck = commonDoCheck;
    buildInputs = commonBuildInputs;
    propagatedBuildInputs = [ ];
    meta = with pkgs.stdenv.lib; {
      homepage = "";
      license = "MIT license";
      description = "library with cross-python path, ini-parsing, io, code, log facilities";
    };
    passthru.top_level = false;
  };



  "pycodestyle" = python.mkDerivation {
    name = "pycodestyle-2.0.0";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/db/b1/9f798e745a4602ab40bf6a9174e1409dcdde6928cf800d3aab96a65b1bbf/pycodestyle-2.0.0.tar.gz";
      sha256= "37f0420b14630b0eaaf452978f3a6ea4816d787c3e6dcbba6fb255030adae2e7";
    };
    doCheck = commonDoCheck;
    buildInputs = commonBuildInputs;
    propagatedBuildInputs = [ ];
    meta = with pkgs.stdenv.lib; {
      homepage = "";
      license = "Expat license";
      description = "Python style guide checker";
    };
    passthru.top_level = false;
  };



  "pycrypto" = python.mkDerivation {
    name = "pycrypto-2.6.1";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/60/db/645aa9af249f059cc3a368b118de33889219e0362141e75d4eaf6f80f163/pycrypto-2.6.1.tar.gz";
      sha256= "f2ce1e989b272cfcb677616763e0a2e7ec659effa67a88aa92b3a65528f60a3c";
    };
    doCheck = commonDoCheck;
    buildInputs = commonBuildInputs;
    propagatedBuildInputs = [ ];
    meta = with pkgs.stdenv.lib; {
      homepage = "";
      license = "";
      description = "Cryptographic modules for Python.";
    };
    passthru.top_level = false;
  };



  "pyflakes" = python.mkDerivation {
    name = "pyflakes-1.2.3";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/54/80/6a641f832eb6c6a8f7e151e7087aff7a7c04dd8b4aa6134817942cdda1b6/pyflakes-1.2.3.tar.gz";
      sha256= "2e4a1b636d8809d8f0a69f341acf15b2e401a3221ede11be439911d23ce2139e";
    };
    doCheck = commonDoCheck;
    buildInputs = commonBuildInputs;
    propagatedBuildInputs = [ ];
    meta = with pkgs.stdenv.lib; {
      homepage = "";
      license = licenses.mit;
      description = "passive checker of Python programs";
    };
    passthru.top_level = false;
  };



  "pytest" = python.mkDerivation {
    name = "pytest-2.9.2";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/f0/ee/6e2522c968339dca7d9abfd5e71312abeeb5ee902e09b4daf44f07b2f907/pytest-2.9.2.tar.gz";
      sha256= "12c18abb9a09a5b2802dba75c7a2d7d6c8c0f1258abd8243e7688415d87ad1d8";
    };
    doCheck = commonDoCheck;
    buildInputs = commonBuildInputs;
    propagatedBuildInputs = [
      self."py"
    ];
    meta = with pkgs.stdenv.lib; {
      homepage = "";
      license = "MIT license";
      description = "pytest: simple powerful testing with Python";
    };
    passthru.top_level = false;
  };



  "pytest-cov" = python.mkDerivation {
    name = "pytest-cov-2.3.0";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/6b/58/14b1ddcfd926199ff1468496bc0268bd37f81d949dcad414ce662538c72d/pytest-cov-2.3.0.tar.gz";
      sha256= "b079fa99d4dd4820ac31fe1863df4053eaff787f65dd04024bd57c2666c35ad4";
    };
    doCheck = commonDoCheck;
    buildInputs = commonBuildInputs;
    propagatedBuildInputs = [
      self."coverage"
      self."pytest"
    ];
    meta = with pkgs.stdenv.lib; {
      homepage = "";
      license = licenses.mit;
      description = "Pytest plugin for measuring coverage.";
    };
    passthru.top_level = false;
  };



  "pytest-runner" = python.mkDerivation {
    name = "pytest-runner-2.8";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/46/6c/ff61a9e0d513222afa3529bdb565a465812b7e50b218a5afd705f46b258c/pytest-runner-2.8.tar.gz";
      sha256= "1ec44deddaa551f85fd563c40a4c483a2609aca1f284a95399566a74d0680d5c";
    };
    doCheck = commonDoCheck;
    buildInputs = commonBuildInputs;
    propagatedBuildInputs = [ ];
    meta = with pkgs.stdenv.lib; {
      homepage = "";
      license = "";
      description = "Invoke py.test as distutils command with dependency resolution";
    };
    passthru.top_level = false;
  };



  "python-dateutil" = python.mkDerivation {
    name = "python-dateutil-2.5.3";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/3e/f5/aad82824b369332a676a90a8c0d1e608b17e740bbb6aeeebca726f17b902/python-dateutil-2.5.3.tar.gz";
      sha256= "1408fdb07c6a1fa9997567ce3fcee6a337b39a503d80699e0f213de4aa4b32ed";
    };
    doCheck = commonDoCheck;
    buildInputs = commonBuildInputs;
    propagatedBuildInputs = [
      self."six"
    ];
    meta = with pkgs.stdenv.lib; {
      homepage = "";
      license = "Simplified BSD";
      description = "Extensions to the standard Python datetime module";
    };
    passthru.top_level = false;
  };



  "python-jose" = python.mkDerivation {
    name = "python-jose-1.0.0";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/2c/17/116863c1725537de4b597f0477d630208412c49039ceb3441e643283e5f7/python-jose-1.0.0.tar.gz";
      sha256= "bded2621dcfce191a07d9acd87ae06a1cb25300d85b3c76d28975f88593265fc";
    };
    doCheck = commonDoCheck;
    buildInputs = commonBuildInputs;
    propagatedBuildInputs = [
      self."ecdsa"
      self."future"
      self."pycrypto"
      self."six"
    ];
    meta = with pkgs.stdenv.lib; {
      homepage = "";
      license = licenses.mit;
      description = "JOSE implementation in Python";
    };
    passthru.top_level = false;
  };



  "requests" = python.mkDerivation {
    name = "requests-2.10.0";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/49/6f/183063f01aae1e025cf0130772b55848750a2f3a89bfa11b385b35d7329d/requests-2.10.0.tar.gz";
      sha256= "63f1815788157130cee16a933b2ee184038e975f0017306d723ac326b5525b54";
    };
    doCheck = commonDoCheck;
    buildInputs = commonBuildInputs;
    propagatedBuildInputs = [ ];
    meta = with pkgs.stdenv.lib; {
      homepage = "";
      license = licenses.asl20;
      description = "Python HTTP for Humans.";
    };
    passthru.top_level = false;
  };



  "scriptworker" = python.mkDerivation {
    name = "scriptworker-0.2.1";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/cb/d1/c3cad279c4a007858f8e2bf4ff82e076b9ce84ab10b54aaa3b6295ff4ccf/scriptworker-0.2.1.tar.gz";
      sha256= "205f54bc205b7302aa04fa451f741a1fd63f5eeaf5347e2ff1dd2f4ec45a06b0";
    };
    doCheck = commonDoCheck;
    buildInputs = commonBuildInputs;
    propagatedBuildInputs = [
      self."aiohttp"
      self."arrow"
      self."defusedxml"
      self."frozendict"
      self."jsonschema"
      self."taskcluster"
      self."virtualenv"
    ];
    meta = with pkgs.stdenv.lib; {
      homepage = "";
      license = "MPL 2.0";
      description = "TaskCluster Script Worker";
    };
    passthru.top_level = false;
  };



  "setuptools-scm" = python.mkDerivation {
    name = "setuptools-scm-1.11.1";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/84/aa/c693b5d41da513fed3f0ee27f1bf02a303caa75bbdfa5c8cc233a1d778c4/setuptools_scm-1.11.1.tar.gz";
      sha256= "8c45f738a23410c5276b0ed9294af607f491e4260589f1eb90df8312e23819bf";
    };
    doCheck = commonDoCheck;
    buildInputs = commonBuildInputs;
    propagatedBuildInputs = [ ];
    meta = with pkgs.stdenv.lib; {
      homepage = "";
      license = licenses.mit;
      description = "the blessed package to manage your versions by scm tags";
    };
    passthru.top_level = false;
  };



  "signtool" = python.mkDerivation {
    name = "signtool-2.0.1";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/72/93/b36601230719a2d552e3c1e5f0ea6c335773e849021b76868408ff124bc8/signtool-2.0.1.tar.gz";
      sha256= "fec69706272b2b141e25ebc7cd4b8e1fcbb9f6b1fbbaf56fb632b802ae5487ee";
    };
    doCheck = commonDoCheck;
    buildInputs = commonBuildInputs;
    propagatedBuildInputs = [
      self."requests"
      self."six"
    ];
    meta = with pkgs.stdenv.lib; {
      homepage = "";
      license = "MPL 2.0";
      description = "Mozilla Signing Tool";
    };
    passthru.top_level = false;
  };



  "six" = python.mkDerivation {
    name = "six-1.10.0";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/b3/b2/238e2590826bfdd113244a40d9d3eb26918bd798fc187e2360a8367068db/six-1.10.0.tar.gz";
      sha256= "105f8d68616f8248e24bf0e9372ef04d3cc10104f1980f54d57b2ce73a5ad56a";
    };
    doCheck = commonDoCheck;
    buildInputs = commonBuildInputs;
    propagatedBuildInputs = [ ];
    meta = with pkgs.stdenv.lib; {
      homepage = "";
      license = licenses.mit;
      description = "Python 2 and 3 compatibility utilities";
    };
    passthru.top_level = false;
  };



  "slugid" = python.mkDerivation {
    name = "slugid-1.0.7";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/dd/96/b05c6d357f8d6932bea2b360537360517d1154b82cc71b8eccb70b28bdde/slugid-1.0.7.tar.gz";
      sha256= "6dab3c7eef0bb423fb54cb7752e0f466ddd0ee495b78b763be60e8a27f69e779";
    };
    doCheck = commonDoCheck;
    buildInputs = commonBuildInputs;
    propagatedBuildInputs = [ ];
    meta = with pkgs.stdenv.lib; {
      homepage = "";
      license = "MPL 2.0";
      description = "Base64 encoded uuid v4 slugs";
    };
    passthru.top_level = false;
  };



  "taskcluster" = python.mkDerivation {
    name = "taskcluster-0.3.4";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/3e/50/bb7659d5cf396f5c78013bb35ac92931c852b0ae3fa738bbd9224b6192ef/taskcluster-0.3.4.tar.gz";
      sha256= "d4fe5e2a44fe27e195b92830ece0a6eb9eb7ad9dc556a0cb16f6f2a6429f1b65";
    };
    doCheck = commonDoCheck;
    buildInputs = commonBuildInputs;
    propagatedBuildInputs = [
      self."aiohttp"
      self."mohawk"
      self."requests"
      self."six"
      self."slugid"
    ];
    meta = with pkgs.stdenv.lib; {
      homepage = "";
      license = "";
      description = "Python client for Taskcluster";
    };
    passthru.top_level = false;
  };



  "vcversioner" = python.mkDerivation {
    name = "vcversioner-2.16.0.0";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/c5/cc/33162c0a7b28a4d8c83da07bc2b12cee58c120b4a9e8bba31c41c8d35a16/vcversioner-2.16.0.0.tar.gz";
      sha256= "dae60c17a479781f44a4010701833f1829140b1eeccd258762a74974aa06e19b";
    };
    doCheck = commonDoCheck;
    buildInputs = commonBuildInputs;
    propagatedBuildInputs = [ ];
    meta = with pkgs.stdenv.lib; {
      homepage = "";
      license = "ISC";
      description = "Use version control tags to discover version numbers";
    };
    passthru.top_level = false;
  };



  "virtualenv" = python.mkDerivation {
    name = "virtualenv-15.0.2";
    src = pkgs.fetchurl {
      url = "https://pypi.python.org/packages/5c/79/5dae7494b9f5ed061cff9a8ab8d6e1f02db352f3facf907d9eb614fb80e9/virtualenv-15.0.2.tar.gz";
      sha256= "fab40f32d9ad298fba04a260f3073505a16d52539a84843cf8c8369d4fd17167";
    };
    doCheck = commonDoCheck;
    buildInputs = commonBuildInputs;
    propagatedBuildInputs = [ ];
    meta = with pkgs.stdenv.lib; {
      homepage = "";
      license = licenses.mit;
      description = "Virtual Python Environment builder";
    };
    passthru.top_level = false;
  };

}
