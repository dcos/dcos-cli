class DcosCli < Formula
  desc "The DC/OS command-line interface"
  homepage "https://docs.mesosphere.com/latest/cli/"
  url "https://github.com/dcos/dcos-cli/archive/0.7.12.tar.gz"
  sha256 "1792b2d3fafb210d023065e13beaf77d274845ccd188a86d9e1fa3c85a704727"

  depends_on "go" => :build
  depends_on "go-bindata" => :build
  depends_on "wget" => :build

  def install
    ENV["GOPATH"] = buildpath
    ENV["NO_DOCKER"] = "1"

    ENV["VERSION"] = "0.7.12"
    ENV["GO_BUILD_TAGS"] = "corecli"

    bin_path = buildpath/"src/github.com/dcos/dcos-cli"

    bin_path.install Dir["*"]
    cd bin_path do
      system "make", "core-download"
      system "make", "core-bundle"
      system "make", "darwin"
      bin.install "build/darwin/dcos"
    end
  end

  test do
    run_output = shell_output("#{bin}/dcos --version 2>&1")
    assert_match "dcoscli.version=0.7.11", run_output
  end
end
