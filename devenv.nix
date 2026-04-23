{ pkgs, ... }: {
  languages.python = {
    enable = true;
    version = "3.12";
    uv.enable = true;
  };

  packages = with pkgs; [
    # 作業基盤
    just
    git

    # コンテナ
    docker
    docker-compose

    # Claude CLI は node 実装 (公式 install script か npm -g で別途)
    nodejs_20

    # CLI ユーティリティ
    ripgrep
    fd
    jq
    yq-go

    # skill importer 用
    gnused
    gawk
    coreutils
  ];

  env = {
    CTF_PROJECT_ROOT = "${builtins.toString ./.}";
  };

  # direnv 連携で cd 時に自動 activate
  # `direnv allow` を一度実行すれば有効
}
