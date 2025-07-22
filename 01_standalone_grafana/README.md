Example 1 — Grafana by itself
===

No additional resources are needed to run this example.
Execute the following command to start Grafana:

```bash
docker run -i -t --rm -p 3000:3000 grafana/grafana:12.0.2
```

You can then access Grafana at `http://localhost:3000` with the default credentials (username: `admin`, password: `admin`).

##### Custom login credentials

```bash
docker run -i -t --rm -p 3000:3000 \
-e GF_SECURITY_ADMIN_USER=a \
-e GF_SECURITY_ADMIN_PASSWORD=a \
grafana/grafana:12.0.2
```

##### Custom login credentials and preinstalled plugin

```bash
docker run -i -t --rm -p 3000:3000 \
-e GF_SECURITY_ADMIN_USER=a \
-e GF_SECURITY_ADMIN_PASSWORD=a \
-e "GF_INSTALL_PLUGINS=grafana-sentry-datasource" \
grafana/grafana:12.0.2
```