
services:
  - type: web
    name: 4k-nova-api
    runtime: docker
    plan: free
    healthCheckPath: /health
    envVars:
      - key: FRONTEND_ORIGINS
        value: "*"
        
