package login

import (
	"encoding/json"
	"fmt"
	"sort"
)

// These are the different login provider types that the DC/OS CLI supports.
const (
	DCOSUIDPassword     = "dcos-uid-password"
	DCOSUIDServiceKey   = "dcos-uid-servicekey"
	DCOSUIDPasswordLDAP = "dcos-uid-password-ldap"
	SAMLSpInitiated     = "saml-sp-initiated"
	OIDCAuthCodeFlow    = "oidc-authorization-code-flow"
	OIDCImplicitFlow    = "oidc-implicit-flow"
)

// These are the different login client methods that the DC/OS CLI supports.
const (
	methodBrowserToken      = "browser-prompt-authtoken"
	methodCredential        = "dcos-credential-post-receive-authtoken"
	methodServiceCredential = "dcos-servicecredential-post-receive-authtoken"
	methodUserCredential    = "dcos-usercredential-post-receive-authtoken"
)

// Provider is a DC/OS login provider.
type Provider struct {
	ID           string         `json:"-"`
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

// Providers is a map of providers as returned by the DC/OS API.
type Providers map[string]*Provider

// UnmarshalJSON unmarshals JSON into a Providers type.
func (p *Providers) UnmarshalJSON(data []byte) error {
	var providers map[string]*Provider
	if err := json.Unmarshal(data, &providers); err != nil {
		return err
	}
	for id, provider := range providers {
		provider.ID = id
	}
	*p = providers
	return nil
}

// Slice returns providers sorted by ID in a slice.
func (p Providers) Slice() []*Provider {
	var ids []string
	for id := range p {
		ids = append(ids, id)
	}
	sort.Strings(ids)

	var providers []*Provider
	for _, id := range ids {
		providers = append(providers, p[id])
	}
	return providers
}

func defaultDCOSUIDPasswordProvider() (provider *Provider) {
	return &Provider{
		ID:           "dcos-users",
		Type:         DCOSUIDPassword,
		Description:  "Default DC/OS login provider",
		ClientMethod: methodUserCredential,
		Config: ProviderConfig{
			StartFlowURL: "/acs/api/v1/auth/login",
		},
	}
}

func defaultOIDCImplicitFlowProvider() (provider *Provider) {
	return &Provider{
		ID:           "dcos-oidc-auth0",
		Type:         OIDCImplicitFlow,
		Description:  "Google, GitHub, or Microsoft",
		ClientMethod: methodBrowserToken,
		Config: ProviderConfig{
			StartFlowURL: "/login?redirect_uri=urn:ietf:wg:oauth:2.0:oob",
		},
	}
}
