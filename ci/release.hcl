source = ["./build/darwin/dcos"]
bundle_id = "com.mesosphere.dcos.cli"

sign {
  application_identity = "Developer ID Application: Mesosphere Inc. (JQJDUUPXFN)"
}

zip {
  output_path = "build/darwin/dcos.zip"
}
