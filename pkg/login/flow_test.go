package login

import (
	"testing"

	"github.com/spf13/afero"
	"github.com/stretchr/testify/require"
)

func TestSelectUIDPasswordProvider(t *testing.T) {
	flow := NewFlow(FlowOpts{})
	flow.flags = NewFlags(afero.NewMemMapFs(), nil, nil)
	flow.flags.username = "hello"
	flow.flags.password = "itsme"

	providers := Providers{}

	providers["login-provider-1"] = &Provider{
		ID:           "login-provider-1",
		Type:         DCOSUIDPassword,
		Description:  "Default DC/OS login provider",
		ClientMethod: methodUserCredential,
		Config: ProviderConfig{
			StartFlowURL: "/acs/api/v1/auth/login",
		},
	}

	providers["login-provider-2"] = &Provider{
		ID:           "login-provider-2",
		Type:         DCOSUIDPassword,
		Description:  "Default DC/OS login provider",
		ClientMethod: methodUserCredential,
		Config: ProviderConfig{
			StartFlowURL: "/acs/api/v1/auth/login",
		},
	}

	provider, err := flow.selectProvider(providers)
	require.NoError(t, err)
	require.True(t, provider == providers["login-provider-1"] || provider == providers["login-provider-2"])
}
