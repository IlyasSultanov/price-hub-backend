FROM quay.io/keycloak/keycloak:25.0

COPY docker/keycloak/entrypoint.sh /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["start-dev"]
