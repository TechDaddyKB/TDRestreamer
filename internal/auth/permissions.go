// Package auth defines deny-by-default application permissions.
package auth

type Principal struct {
	UserID      string `json:"user_id"`
	TenantID    string `json:"tenant_id"`
	Role        string `json:"role"`
	EditGranted bool   `json:"edit_granted"`
}

func (p Principal) Allows(tenant, action string) bool {
	// Admin access is deliberately tenant-scoped too; switching context must be audited.
	if p.UserID == "" || tenant == "" || p.TenantID != tenant {
		return false
	}
	switch action {
	case "view":
		return p.Role == "admin" || p.Role == "streamer" || p.Role == "operator" || p.Role == "viewer"
	case "operate":
		return p.Role == "admin" || p.Role == "streamer" || p.Role == "operator"
	case "edit":
		return p.Role == "admin" || p.Role == "streamer" || (p.Role == "operator" && p.EditGranted)
	case "secrets", "members":
		return p.Role == "admin" || p.Role == "streamer"
	case "infrastructure":
		return p.Role == "admin"
	default:
		return false
	}
}
