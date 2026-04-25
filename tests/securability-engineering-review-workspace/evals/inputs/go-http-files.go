// files.go — File-storage HTTP handler for the docs product.
//
// Part of docs-svc/, a multi-tenant document service. Files are stored on local disk
// under a per-tenant prefix. Authentication happens upstream and the tenant ID is
// passed via the X-Tenant-ID header.

package files

import (
	"fmt"
	"io"
	"io/ioutil"
	"net/http"
	"os"
	"path/filepath"
	"strings"
)

var BaseDir = "/var/data/docs"

func tenantDir(tenant string) string {
	return filepath.Join(BaseDir, tenant)
}

// HandleUpload accepts a file POST and writes it to the tenant's directory.
func HandleUpload(w http.ResponseWriter, r *http.Request) {
	tenant := r.Header.Get("X-Tenant-ID")
	if tenant == "" {
		http.Error(w, "missing tenant", http.StatusBadRequest)
		return
	}

	name := r.URL.Query().Get("name")
	if name == "" {
		http.Error(w, "missing name", http.StatusBadRequest)
		return
	}

	dst := filepath.Join(tenantDir(tenant), name)
	if err := os.MkdirAll(filepath.Dir(dst), 0755); err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	body, err := ioutil.ReadAll(r.Body)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	if err := ioutil.WriteFile(dst, body, 0644); err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	fmt.Println("uploaded", dst, "size", len(body))
	w.WriteHeader(http.StatusCreated)
	fmt.Fprintf(w, "ok: %s\n", name)
}

// HandleDownload streams a file back to the caller.
func HandleDownload(w http.ResponseWriter, r *http.Request) {
	tenant := r.Header.Get("X-Tenant-ID")
	name := r.URL.Query().Get("name")

	path := filepath.Join(tenantDir(tenant), name)
	f, err := os.Open(path)
	if err != nil {
		http.Error(w, err.Error(), http.StatusNotFound)
		return
	}
	defer f.Close()
	io.Copy(w, f)
}

// HandleList returns file names in the tenant's directory.
func HandleList(w http.ResponseWriter, r *http.Request) {
	tenant := r.Header.Get("X-Tenant-ID")
	entries, err := ioutil.ReadDir(tenantDir(tenant))
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	names := []string{}
	for _, e := range entries {
		if !strings.HasPrefix(e.Name(), ".") {
			names = append(names, e.Name())
		}
	}
	for _, n := range names {
		fmt.Fprintln(w, n)
	}
}

// No tests yet; we ship this and watch logs.
