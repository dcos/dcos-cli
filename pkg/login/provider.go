package login

import "fmt"

// These are the different login provider types that DC/OS supports.
const (
	DCOSUIDPassword     = "dcos-uid-password"
	DCOSUIDServiceKey   = "dcos-uid-servicekey"
	DCOSUIDPasswordLDAP = "dcos-uid-password-ldap"
	SAMLSpInitiated     = "saml-sp-initiated"
	OIDCAuthCodeFlow    = "oidc-authorization-code-flow"
	OIDCImplicitFlow    = "oidc-implicit-flow"
)

// Provider is a DC/OS login provider.
type Provider struct {
	Type         string         `json:"authentication-type"`
	ClientMethod string         `json:"client-method"`
	Config       ProviderConfig `json:"config"`
	Description  string         `json:"description"`
}

// String converts a login provider to a string.
func (provider *Provider) String() string {
	switch provider.Type {
	case DCOSUIDPassword:
		return "Log in using a standard DC/OS user account (username and password)"
	case DCOSUIDServiceKey:
		return "Log in using a DC/OS service user account (username and private key)"
	case DCOSUIDPasswordLDAP:
		return "Log in using an LDAP user account (username and password)"
	case SAMLSpInitiated:
		return fmt.Sprintf("Log in using SAML 2.0 (%s)", provider.Description)
	case OIDCImplicitFlow:
		return fmt.Sprintf("Log in using OpenID Connect (%s)", provider.Description)
	case OIDCAuthCodeFlow:
		return fmt.Sprintf("Log in using OpenID Connect (%s)", provider.Description)
	default:
		return ""
	}
}

// ProviderConfig holds login provider specific configuration.
type ProviderConfig struct {
	StartFlowURL string `json:"start_flow_url"`
}

func defaultDCOSUIDPasswordProvider() (provider *Provider) {
	return &Provider{
		Type:         DCOSUIDPassword,
		Description:  "Default DC/OS login provider",
		ClientMethod: "dcos-usercredential-post-receive-authtoken",
		Config: ProviderConfig{
			StartFlowURL: "/acs/api/v1/auth/login",
		},
	}
}

func defaultOIDCImplicitFlowProvider() (provider *Provider) {
	return &Provider{
		Type:         OIDCImplicitFlow,
		Description:  "Google, GitHub, or Microsoft",
		ClientMethod: "browser-prompt-authtoken",
		Config: ProviderConfig{
			StartFlowURL: "/login?redirect_uri=urn:ietf:wg:oauth:2.0:oob",
		},
	}
}
