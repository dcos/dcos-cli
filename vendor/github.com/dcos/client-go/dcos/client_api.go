/*
 * DC/OS
 *
 * DC/OS API
 *
 * API version: 1.0.0
 */

package dcos

import (
	"context"
	"crypto/rsa"
	"crypto/x509"
	"encoding/pem"
	"fmt"
	"net/http"
	"time"

	"gopkg.in/square/go-jose.v2"
	"gopkg.in/square/go-jose.v2/jwt"
)

/*
ServiceAccountOptions describe the service account parameters.
*/
type ServiceAccountOptions struct {
	LoginEndpoint string        `json:"login_endpoint"`
	PrivateKey    string        `json:"private_key"`
	Scheme        string        `json:"scheme"`
	UID           string        `json:"uid"`
	Expire        time.Duration `json:"expire"`
}

/*
LoginWithServiceAccount Logs in using a service account secret, as created using
dcos security secrets create-sa-secret.

* @param opt ServiceAccountOptions - the options for logging in with service account
*/
func (c *APIClient) LoginWithServiceAccount(ctx context.Context, opt ServiceAccountOptions) (IamAuthToken, *http.Response, error) {
	var (
		localEmptyIamToken IamAuthToken
	)

	// We currently only support RS256 algorithm
	if opt.Scheme != "RS256" {
		return localEmptyIamToken, nil, fmt.Errorf("Unsupported signing algorithm scheme")
	}

	block, _ := pem.Decode([]byte(opt.PrivateKey))
	if block == nil || block.Type != "PRIVATE KEY" {
		return localEmptyIamToken, nil, fmt.Errorf("Invalid private key contents given")
	}

	parseResult, err := x509.ParsePKCS8PrivateKey(block.Bytes)
	if err != nil {
		return localEmptyIamToken, nil, err
	}

	key, ok := parseResult.(*rsa.PrivateKey)
	if !ok {
		return localEmptyIamToken, nil, fmt.Errorf("Invalid private key contents given")
	}

	// Create a new JWT signer
	sig, err := jose.NewSigner(jose.SigningKey{
		Algorithm: jose.RS256,
		Key:       key,
	}, (&jose.SignerOptions{}).WithType("JWT"))
	if err != nil {
		return localEmptyIamToken, nil, err
	}

	// if expire is not set or negative value, default to 5 days.
	if opt.Expire < 1 {
		opt.Expire = time.Duration(time.Hour * 24 * 5)
	}

	// Create the JSON token and sign it
	cl := struct {
		UID string `json:"uid"`
		Exp int64  `json:"exp"`
	}{
		opt.UID,
		time.Now().Add(opt.Expire).Unix(),
	}
	tokenStr, err := jwt.Signed(sig).Claims(cl).CompactSerialize()
	if err != nil {
		return localEmptyIamToken, nil, err
	}

	// Create an IamLoginObject and delegate to Login method
	loginObj := IamLoginObject{
		Uid:   opt.UID,
		Token: tokenStr,
	}

	return c.IAM.Login(ctx, loginObj)
}
