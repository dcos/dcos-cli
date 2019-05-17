package auth

import (
	"bytes"
	"testing"

	"github.com/dcos/dcos-cli/pkg/login"

	"github.com/dcos/dcos-cli/pkg/cli"
	"github.com/dcos/dcos-cli/pkg/mock"
	"github.com/olekukonko/tablewriter"
	"github.com/stretchr/testify/require"
)

func TestAuthListProvidersTable(t *testing.T) {
	fixtures := []struct {
		cluster     mock.Cluster
		expectTable func(table *tablewriter.Table)
	}{
		{
			mock.Cluster{
				AuthChallenge: "acsjwt",
				LoginProviders: login.Providers{
					"dcos-users":   &login.Provider{Type: login.DCOSUIDPassword},
					"dcos-service": &login.Provider{Type: login.DCOSUIDServiceKey},
				}},
			func(table *tablewriter.Table) {
				table.Append([]string{"dcos-service", "Log in using a DC/OS service user account (username and private key)"})
				table.Append([]string{"dcos-users", "Log in using a standard DC/OS user account (username and password)"})
			},
		},
		{
			mock.Cluster{AuthChallenge: "acsjwt"},
			func(table *tablewriter.Table) {
				table.Append([]string{"dcos-users", "Log in using a standard DC/OS user account (username and password)"})
			},
		},
		{
			mock.Cluster{AuthChallenge: "oauthjwt"},
			func(table *tablewriter.Table) {
				table.Append([]string{"dcos-oidc-auth0", "Log in using OpenID Connect (Google, GitHub, or Microsoft)"})
			},
		},
	}

	for _, fixture := range fixtures {
		ts := mock.NewTestServer(fixture.cluster)
		defer ts.Close()

		var out bytes.Buffer
		env := mock.NewEnvironment()
		env.Out = &out

		cmd := newCmdAuthListProviders(cli.NewContext(env))
		cmd.SetArgs([]string{ts.URL})

		err := cmd.Execute()
		require.NoError(t, err)

		var exp bytes.Buffer
		table := cli.NewTable(&exp, []string{"PROVIDER ID", "LOGIN METHOD"})
		fixture.expectTable(table)
		table.Render()
		require.Equal(t, exp.String(), out.String())
	}
}
