{{/* Name helpers */}}
{{- define "claude.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "claude.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "claude.collectorName" -}}
{{- printf "%s-otel-%s" (include "claude.fullname" .) .Values.team | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "claude.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{- default (include "claude.fullname" .) .Values.serviceAccount.name -}}
{{- else -}}
{{- default "default" .Values.serviceAccount.name -}}
{{- end -}}
{{- end -}}

{{/* Common labels */}}
{{- define "claude.labels" -}}
app.kubernetes.io/name: {{ include "claude.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" }}
team: {{ .Values.team | quote }}
{{- end -}}

{{/* OTLP endpoint the agent exports to (in-cluster collector unless overridden) */}}
{{- define "claude.otelEndpoint" -}}
{{- if .Values.otelEndpoint -}}
{{- .Values.otelEndpoint -}}
{{- else -}}
{{- $scheme := ternary "https" "http" .Values.certManager.enabled -}}
{{- printf "%s://%s.%s:%v" $scheme (include "claude.collectorName" .) .Release.Namespace (.Values.collector.service.otlpHttpPort) -}}
{{- end -}}
{{- end -}}

{{/* Pod securityContext — render only fields that are non-null */}}
{{- define "claude.podSecurityContext" -}}
{{- with .Values.securityContext.pod -}}
{{- if not (kindIs "invalid" .runAsNonRoot) }}
runAsNonRoot: {{ .runAsNonRoot }}
{{- end }}
{{- if not (kindIs "invalid" .runAsUser) }}
runAsUser: {{ .runAsUser }}
{{- end }}
{{- if not (kindIs "invalid" .runAsGroup) }}
runAsGroup: {{ .runAsGroup }}
{{- end }}
{{- if not (kindIs "invalid" .fsGroup) }}
fsGroup: {{ .fsGroup }}
{{- end }}
{{- with .seccompProfile }}
seccompProfile:
  {{- toYaml . | nindent 2 }}
{{- end }}
{{- end -}}
{{- end -}}

{{/* Container securityContext */}}
{{- define "claude.containerSecurityContext" -}}
{{- toYaml .Values.securityContext.container -}}
{{- end -}}
