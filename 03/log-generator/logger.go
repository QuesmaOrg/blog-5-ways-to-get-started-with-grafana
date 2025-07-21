// Copyright Quesma, licensed under the Elastic License 2.0.
// SPDX-License-Identifier: Elastic-2.0
package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"log"
	"math/rand"
	"net/http"
	"time"
)

const url = "http://loki:3100/loki/api/v1/push"

func main() {
	hostNames := []string{"zeus", "cassandra", "hercules",
		"oracle", "athena", "jupiter", "poseidon", "hades", "artemis", "apollo", "demeter",
		"dionysus", "hephaestus", "hermes", "hestia", "iris", "nemesis", "pan", "persephone", "prometheus", "selen"}

	serviceNames := []string{"frontend", "backend", "database", "cache", "queue", "monitoring", "loadbalancer", "proxy",
		"storage", "auth", "api", "web", "worker", "scheduler", "cron", "admin", "service", "gateway", "service", "service", "service"}

	sourceNames := []string{"kubernetes", "ubuntu", "debian", "centos", "redhat", "fedora", "arch", "gentoo", "alpine", "suse",
		"rhel", "coreos", "docker", "rancher", "vmware", "xen", "hyperv", "openstack", "aws", "gcp", "azure", "digitalocean"}

	severityNames := []string{"info", "info", "info", "info", "info", "info", "warning", "error", "critical", "debug", "debug", "debug"}

	messageNames := []string{"User logged in", "User logged out", "User created", "User deleted", "User updated",
		"User password changed", "User password reset", "User password reset requested", "User password reset failed"}

	for {
		time.Sleep(time.Duration(1000+rand.Intn(2000)) * time.Millisecond)

		timestamp := time.Now()
		severity := severityNames[rand.Intn(len(severityNames))]
		source := sourceNames[rand.Intn(len(sourceNames))]
		serviceName := serviceNames[rand.Intn(len(serviceNames))]
		hostName := hostNames[rand.Intn(len(hostNames))]
		message := messageNames[rand.Intn(len(messageNames))]

		// Create Loki push request format
		logEntry := map[string]interface{}{
			"streams": []map[string]interface{}{
				{
					"stream": map[string]string{
						"severity":     severity,
						"source":       source,
						"service_name": serviceName,
						"host_name":    hostName,
						"job":          "log-generator",
					},
					"values": [][]string{
						{
							fmt.Sprintf("%d", timestamp.UnixNano()),
							message,
						},
					},
				},
			},
		}

		body, err := json.Marshal(logEntry)
		if err != nil {
			log.Fatal(err)
		}

		resp, err := http.Post(url, "application/json", bytes.NewBuffer(body))
		if err != nil {
			log.Fatal(err)
		}

		resp.Body.Close()
	}
}
