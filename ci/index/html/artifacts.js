(function() {
  // The 'Artifact' object abstracts the
  // properties of a release artifact for the CLI.
  this.Artifact = function(path) {
    this.type = "";
    this.name = "";
    this.platform = "";
    this.arch = "";
    this.version = null;
    this.path = path;

    // The 'BinaryVersion' object abstracts the
    // properties of the version for a CLI binary.
    var BinaryVersion = function(major, minor, patch) {
      this.major = major;
      this.minor = major + "." + minor;
      this.patch = major + "." + minor + "." + patch;
    };
    BinaryVersion.prototype.toString = function() {
        return this.patch
    };

    // The 'PluginVersion' object abstracts the
    // properties of the version for a CLI plugin.
    var PluginVersion = function(dcos, patch) {
      this.dcos = dcos;
      this.patch = patch;
    };
    PluginVersion.prototype.toString = function() {
        return this.dcos + "-patch." + this.patch;
    };

    // The 'constructor' function constructs a CLI
    // artifact from a path to a CLI artifact.
    var constructor = function(self, path) {
      parts = path.split('/');

      if (parts[0] !== "releases") {
          throw("Invalid path: Paths to artifacts must follow the scheme" +
                " 'releases/...': " + path);
      }

      switch(parts[1]) {
        case "binaries":
          self.type = "binary";
          break;
        case "plugins":
          self.type = "plugin";
          break;
        default:
          throw("Invalid path: Unrecognized <type> '" + parts[1] + "'" +
                " in scheme 'releases/<type>/... for path '" + path + "'");
      };

      if (self.type === "binary" && parts.length != 7) {
          throw("Invalid path: Paths to 'binaries' must follow the scheme" +
                " 'releases/binaries/<name>/<platform>/<arch>/<version>/<name>{.exe}" +
                " for path '" + path + "'");
      }

      if (self.type === "plugin" && parts.length != 6) {
          throw("Invalid path: Paths to 'plugins' must follow the scheme" +
                " 'releases/plugins/<name>/<platform>/<arch>/<name>-<dcos-version>-patch.<patch-version>.zip'" +
                " for path '" + path + "'");
      }

      self.name = parts[2];

      if (["darwin", "linux", "windows"].indexOf(parts[3]) === -1) {
          throw("Invalid path: Unrecognized <platform> '" + parts[3] + "'" +
                " in scheme 'releases/<type>/<name>/<platform>/...'" +
                " for path '" + path + "'");
      }

      self.platform = parts[3];

      if (["x86-64"].indexOf(parts[4]) === -1) {
          throw("Invalid path: Unrecognized <arch> '" + parts[4] + "'" +
                " in scheme 'releases/<type>/<name>/<platform>/<arch>/...'" +
                " for path '" + path + "'");
      }

      self.arch = parts[4];

      if (self.type === "binary") {
          var regex = /(\d+)\.(\d+).(\d+)/;
          matches = regex.exec(parts[5]);

          if (matches === null) {
              throw("Invalid path: The binary version '" + parts[5] + "'" +
                    " does not match '<major>.<minor>.<patch>' as all" +
                    " numerical digits in scheme " +
                    " 'releases/<type>/<name>/<platform>/<arch>/<version>/...'" +
                    " for path '" + path + "'");
          }

          self.version = new BinaryVersion(matches[1], matches[2], matches[3]);

          if (parts[6] !== self.name && parts[6] !== self.name + ".exe") {
              throw("Invalid path: The binary name '" + parts[6] + "'" +
                    " does not match '<name>{.exe}' in scheme" +
                    " 'releases/<type>/<name>/<platform>/<arch>/<version>/<name>{.exe}'" +
                    " for path '" + path + "'");
          }
      }

      if (self.type == "plugin") {
          var regex = /(.+)-(\d+\.\d+)-patch\.(\d+)\.zip/;
          matches = regex.exec(parts[5]);

          if (matches === null || matches[1] !== self.name) {
              throw("Invalid path: The plugin name '" + parts[5] + "'" +
                    " does not match" +
                    " '<name>-<dcos-version>-patch.<patch-version>.zip' in scheme" +
                    " 'releases/<type>/<name>/<platform>/<arch>/<version>/<name>-<dcos-version>-patch.<patch-version>.zip'" +
                    " for path '" + path + "'");
          }

          self.version = new PluginVersion(matches[2], matches[3]);
      }
    };

    // The 'anchor' function constructs an HTML anchor to
    // an artifact's path, using 'text' as the placeholder
    // text. If 'text' is 'null', the path itself is used as
    // the placeholder text.
    this.anchor = function(text=null) {
      if (text === null) {
        text = this.path
      }
      return '<a href="' + this.path + '">' + text + '</a>';
    }

    constructor(this, path);
  };

  // The 'Artifacts' object defines a collection of
  // functions for working with a set 'Artifact' objects.
  this.Artifacts = function(artifacts) {
    this.artifacts = artifacts;

    // The 'Binaries' object defines a collection of functions
    // for working with a set of binary 'Artifact' objects.
    var Binaries = function(binaries) {
      this.binaries = binaries;

      // List all binary artifacts.
      this.list = function() {
        return this.binaries;
      };

      // List unique major versions across all binaries.
      this.majorVersions = function() {
        var versions = [];
        $.each(this.binaries, function(_, binary) {
          if (versions.indexOf(binary.version.major) === -1) {
            versions.push(binary.version.major);
          }
        });
        return versions;
      };

      // List unique minor versions across all binaries.
      this.minorVersions = function() {
        var versions = [];
        $.each(this.binaries, function(_, binary) {
          version = binary.version.minor;
          if (versions.indexOf(version) === -1) {
            versions.push(version);
          }
        });
        return versions;
      };

      // List unique patch versions across all binaries.
      this.patchVersions = function() {
        var versions = [];
        $.each(this.binaries, function(_, binary) {
          if (versions.indexOf(binary.version.toString()) === -1) {
            versions.push(binary.version.toString());
          }
        });
        return versions;
      };

      // List unique versions across all binaries.
      this.versions = this.patchVersions;

      // List unique platforms across all binaries.
      this.platforms = function() {
        var platforms = [];
        $.each(this.binaries, function(_, binary) {
          if (platforms.indexOf(binary.platform) === -1) {
            platforms.push(binary.platform);
          }
        });
        return platforms;
      };

      // List unique architectures across all binaries.
      this.architectures = function() {
        var architectures = [];
        $.each(this.binaries, function(_, binary) {
          if (architectures.indexOf(binary.arch) === -1) {
            architectures.push(binary.arch);
          }
        });
        return architectures;
      };

      // List unique names across all binaries.
      this.names = function() {
        var names = [];
        $.each(this.binaries, function(_, binary) {
          if (names.indexOf(binary.name) === -1) {
            names.push(binary.name);
          }
        });
        return names;
      };
    };

    // The 'Plugins' object defines a collection of functions
    // for working with a set of plugin 'Artifact' objects.
    var Plugins = function(plugins) {
      this.plugins = plugins;

      // List all plugin artifacts.
      this.list = function() {
        return this.plugins;
      };

      // List unique DC/OS versions across all plugins.
      this.dcosVersions = function() {
        var versions = [];
        $.each(this.plugins, function(_, plugin) {
          if (versions.indexOf(plugin.version.dcos) === -1) {
            versions.push(plugin.version.dcos);
          }
        });
        return versions;
      };

      // List unique patch versions across all plugins.
      this.patchVersions = function() {
        var versions = [];
        $.each(this.plugins, function(_, plugin) {
          if (versions.indexOf(plugin.version.toString()) === -1) {
            versions.push(plugin.version.toString());
          }
        });
        return versions;
      };

      // List unique versions across all plugins.
      this.versions = this.patchVersions;

      // List unique platforms across all plugins.
      this.platforms = function() {
        var platforms = [];
        $.each(this.plugins , function(_, plugin) {
          if (platforms.indexOf(plugin.platform) === -1) {
            platforms.push(plugin.platform);
          }
        });
        return platforms;
      };

      // List unique architectures across all plugins.
      this.architectures = function() {
        var architectures = [];
        $.each(this.plugins , function(_, plugin) {
          if (architectures.indexOf(plugin.arch) === -1) {
            architectures.push(plugin.arch);
          }
        });
        return architectures;
      };

      // List unique names across all plugins.
      this.names = function() {
        var names = [];
        $.each(this.plugins, function(_, plugin) {
          if (names.indexOf(plugin.name) === -1) {
            names.push(plugin.name);
          }
        });
        return names;
      };
    };

    // The 'binaries' function returns a 'Binaries'
    // object representing the set of binary artifacts.
    this.binaries = function() {
      var binaries = this.artifacts.filter(function(artifact) {
        return artifact.type == "binary";
      });
      return new Binaries(binaries);
    };

    // The 'plugins' function returns a 'Plugins'
    // object representing the set of plugin artifacts.
    this.plugins = function() {
      var plugins = this.artifacts.filter(function(artifact) {
        return artifact.type == "plugin";
      });
      return new Plugins(plugins);
    };

    // The 'platforms' function returns a list of
    // platforms across all binaries and plugins.
    this.platforms = function() {
      var platforms = [];
      $.each(this.artifacts, function(_, artifact) {
        if (platforms.indexOf(artifact.platform) === -1) {
          platforms.push(artifact.platform);
        }
      });
      return platforms;
    };

    // The 'architectures' function returns a list of
    // architectures across all binaries and plugins.
    this.architectures = function() {
      var architectures = [];
      $.each(this.artifacts, function(_, artifact) {
        if (architectures.indexOf(artifact.arch) === -1) {
          architectures.push(artifact.arch);
        }
      });
      return architectures;
    };
  };

  // The 'FetchArtifacts' function fetches a list of CLI artifacts from
  // a JSON file and creates an 'Artifacts' object representing them.
  this.FetchArtifacts = function(source, callback) {
    var artifacts = [];

    $.getJSON(source, function(data) {
      $.each(data, function(key, val) {
        if (key != "artifacts") {
          throw("Unknown key in '" + this.source + "': " + key);
        }

        $.each(val, function(i, path) {
          artifacts.push(new Artifact(path));
        });
      });

      callback(new Artifacts(artifacts));
    });
  };
})();
