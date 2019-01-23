(function() {
  // The 'getQueryParams' function parses the query string parameters from the
  // URL of the current page and returns them as a dictionary. If a specific
  // key is passed as a parameter, then it only returns the value of that key
  // instead of the entire dictionary.
  var getQueryParams = function(k) {
    var p={};
    location.search.replace(/[?&]+([^=&]+)=([^&]*)/gi,function(s,k,v){p[k]=v});
    return k ? p[k] : p;
  };

  // The 'setQueryParams' function takes a dictionary and updates the URL query
  // parameters with the key-value pairs contained within. It preserves any
  // query parameters not part of the dictionary and overwrites ones that are
  // in the dictionary with new values.
  //
  // Note: We only support setting these parameters in
  // modern browsers that support 'history.pushState'.
  var setQueryParams = function(dict) {
    params = $.extend(getQueryParams(), dict);

    url = window.location.protocol + "//" +
          window.location.host +
          window.location.pathname +
          '?' + $.param(params);

    if (history.pushState) {
      window.history.pushState({ path: url }, '', url);
    } else {
      console.log("Unable to set URL query parameters" +
                  " without support for 'history.pushState()'");
    }
  };

  // The 'selectBox' function builds up a select box of a specific 'type' using
  // 'dict' to fill in the value and text of each option in the select box. If
  // 'type' appears as a query parameter key and it's value matches the value
  // of one of the options in the select box, we mark that option as selected.
  var selectBox = function(type, dict) {
    var s = "<select>"
    $.each(dict, function(val, text) {
      var selected = "";
      if (val === getQueryParams(type)) {
          selected = "selected";
      }
      s += '<option ' + selected + ' value="' + val + '">' + text + '</option>';
    });
    return s + "</select>";
  };

  // The 'RenderBrowser' function builds out the file browser from the
  // contents of the artifacts contained in the JSON 'source' input file.
  this.RenderBrowser = function(source) {
    // Fetch all of the artifacts from the 'source' JSON file.
    FetchArtifacts(source, function(artifacts) {
      // Separate artifacts into binaries and plugins.
      var binaries = artifacts.binaries();
      var plugins = artifacts.plugins();

      // Grab a reference to the different sections in the DOM.
      var $platforms = $("#platforms");
      var $architectures = $("#architectures");
      var $binaries = $("#binaries");
      var $plugins = $("#plugins");

      // Set headings for the binaries and plugins sections.
      $binaries.find("[name=header]").text("Binaries");
      $plugins.find("[name=header]").text("Plugins");

      // Build the 'platforms' select box.
      var platforms = { all: "All Platforms" };
      $.each(artifacts.platforms(), function(_, platform) {
          platforms[platform] = platform;
      });
      $platforms.append(selectBox("platform", platforms));

      // Build the 'architectures' select box.
      var architectures = { all: "All Architectures" };
      $.each(artifacts.architectures(), function(_, architecture) {
          architectures[architecture] = architecture;
      });
      $architectures.append(selectBox("architecture", architectures));

      // Build the 'binary' select box.
      var names = { all: "All Binaries" };
      $.each(binaries.names(), function(_, name) {
          names[name] = name;
      });
      $binaries.find("[name=names]").append(selectBox("binary", names));

      // Build the 'cli' select box.
      var versions = { all: "All CLI Versions" };
      $.each(binaries.minorVersions(), function(_, version) {
          versions[version] = version;
      });
      $binaries.find("[name=versions]").append(selectBox("cli", versions));

      // Build the 'plugin' select box.
      var names = { all: "All Plugins" };
      $.each(plugins.names(), function(_, name) {
          names[name] = name;
      });
      $plugins.find("[name=names]").append(selectBox("plugin", names));

      // Build the 'dcos' select box.
      var versions = { all: "All DC/OS Versions" };
      $.each(plugins.dcosVersions(), function(_, version) {
          versions[version] = version;
      });
      $plugins.find("[name=versions]").append(selectBox("dcos", versions));

      // Trigger a reset of the URL query parameters and refresh
      // the binary and plugin listings everytime a select box changes.
      var $selections = $(".selection select");
      $(".selection select").change(function() {
        var platform = $platforms.find("select").val()
        var architecture = $architectures.find("select").val()
        var binary_name = $binaries.find("[name=names] select").val()
        var cli_version = $binaries.find("[name=versions] select").val()
        var plugin_name = $plugins.find("[name=names] select").val()
        var dcos_version = $plugins.find("[name=versions] select").val()

        // Reset the URL query parameters.
        setQueryParams({
          "platform": platform,
          "architecture": architecture,
          "binary": binary_name,
          "cli": cli_version,
          "plugin": plugin_name,
          "dcos": dcos_version
        })

        // Update the binary listings.
        var $listings = $binaries.find("[name=listings]")
        $listings.empty();
        $.each(binaries.list(), function(_, binary) {
            if (platform !== "all" &&
                platform !== binary.platform) {
              return
            }
            if (architecture !== "all" &&
                architecture !== binary.arch) {
              return
            }
            if (binary_name !== "all" &&
                binary_name !== binary.name) {
              return
            }
            if (cli_version !== "all" &&
                cli_version !== binary.version.minor) {
              return
            }
            $listings.append(binary.anchor() + "<br/>")
        });

        // Update the plugin listings.
        var $listings = $plugins.find("[name=listings]")
        $listings.empty();
        $.each(plugins.list(), function(_, plugin) {
            if (platform !== "all" &&
                platform !== plugin.platform) {
              return
            }
            if (architecture !== "all" &&
                architecture !== plugin.arch) {
              return
            }
            if (plugin_name !== "all" &&
                plugin_name !== plugin.name) {
              return
            }
            if (dcos_version !== "all" &&
                dcos_version !== plugin.version.dcos) {
              return
            }
            $listings.append(plugin.anchor() + "<br/>")
        });
      });

      // Trigger a change the first time the page is loaded.
      $selections.first().trigger("change");
    });
  };
})();
