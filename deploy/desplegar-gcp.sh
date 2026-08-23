#!/usr/bin/env bash
# =============================================================================
#  Despliegue de Logic Detective en una VM de Google Cloud Platform
# =============================================================================
#  Uso:
#      ./deploy/desplegar-gcp.sh                # crea la VM y despliega
#      ./deploy/desplegar-gcp.sh --actualizar   # vuelve a subir el código
#      ./deploy/desplegar-gcp.sh --apagar       # detiene la VM (deja de cobrar)
#      ./deploy/desplegar-gcp.sh --encender     # la vuelve a levantar
#      ./deploy/desplegar-gcp.sh --eliminar     # borra VM, disco y regla
#      ./deploy/desplegar-gcp.sh --estado       # qué hay creado y su IP
#
#  COSTO
#      La configuración por omisión es la capa "Always Free" de GCP:
#
#        e2-micro          1 instancia al mes gratis, solo en us-west1,
#                          us-central1 o us-east1
#        30 GB pd-standard incluidos en la misma capa gratuita
#        IP externa        ~USD 0.004/hora, es lo único que sí se cobra
#                          (~USD 0.70 por semana)
#
#      O sea que sostener esto una semana cuesta menos de un dólar, y sale del
#      crédito de bienvenida si todavía está vigente. Al terminar la
#      calificación conviene correr --eliminar para no dejar nada corriendo.
#
#  Requisitos previos (una sola vez):
#      1. Cuenta de facturación abierta y vinculada al proyecto.
#      2. gcloud autenticado:  gcloud auth login
set -euo pipefail

PROYECTO="${PROYECTO:-$(gcloud config get-value project 2>/dev/null)}"
# us-central1 es una de las tres regiones donde la e2-micro es gratis.
ZONA="${ZONA:-us-central1-a}"
INSTANCIA="${INSTANCIA:-logic-detective}"
TIPO="${TIPO:-e2-micro}"
DISCO_GB="${DISCO_GB:-30}"
ETIQUETA="logic-detective"
REGLA="permitir-$ETIQUETA"
RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

paso() { printf '\n\033[1;34m==>\033[0m %s\n' "$1"; }

if [ -z "$PROYECTO" ]; then
    echo "No hay proyecto configurado. Corré: gcloud config set project <ID>" >&2
    exit 1
fi

gcp() { gcloud "$@" --project "$PROYECTO"; }
existe_instancia() { gcp compute instances describe "$INSTANCIA" --zone "$ZONA" >/dev/null 2>&1; }
ip_publica() {
    gcp compute instances describe "$INSTANCIA" --zone "$ZONA" \
        --format 'get(networkInterfaces[0].accessConfigs[0].natIP)'
}

# ---------------------------------------------------------------------------
#  Subcomandos de ciclo de vida
# ---------------------------------------------------------------------------
case "${1:-}" in
    --apagar)
        paso "Deteniendo $INSTANCIA"
        # Apagada solo se paga el disco (30 GB pd-standard, dentro de la capa
        # gratuita), ni la vCPU ni la IP.
        gcp compute instances stop "$INSTANCIA" --zone "$ZONA"
        echo "Detenida. Los contenedores vuelven solos al encenderla: llevan restart: unless-stopped."
        exit 0
        ;;
    --encender)
        paso "Encendiendo $INSTANCIA"
        gcp compute instances start "$INSTANCIA" --zone "$ZONA"
        echo "Interfaz: http://$(ip_publica):8080"
        echo "La IP cambia en cada encendido: es efímera."
        exit 0
        ;;
    --eliminar)
        paso "Eliminando $INSTANCIA, su disco y la regla de firewall"
        gcp compute instances delete "$INSTANCIA" --zone "$ZONA" --quiet || true
        gcp compute firewall-rules delete "$REGLA" --quiet || true
        echo "Listo. No queda nada facturable."
        exit 0
        ;;
    --estado)
        gcp compute instances list --filter "name=$INSTANCIA" || true
        existe_instancia && echo "Interfaz: http://$(ip_publica):8080"
        exit 0
        ;;
esac

# ---------------------------------------------------------------------------
#  Crear la infraestructura (se salta lo que ya exista)
# ---------------------------------------------------------------------------
if [ "${1:-}" != "--actualizar" ]; then
    paso "Habilitando la API de Compute Engine"
    gcp services enable compute.googleapis.com

    if ! existe_instancia; then
        paso "Creando $INSTANCIA ($TIPO, ${DISCO_GB}GB pd-standard) en $ZONA"
        # pd-standard y no pd-balanced: el balanceado no entra en la capa
        # gratuita. Es más lento, y para este proyecto da igual.
        gcp compute instances create "$INSTANCIA" \
            --zone "$ZONA" \
            --machine-type "$TIPO" \
            --image-family ubuntu-2204-lts \
            --image-project ubuntu-os-cloud \
            --boot-disk-size "${DISCO_GB}GB" \
            --boot-disk-type pd-standard \
            --tags "$ETIQUETA" \
            --metadata-from-file startup-script="$RAIZ/deploy/arranque-vm.sh"
    else
        paso "$INSTANCIA ya existe, se reutiliza"
    fi

    # 8080 es la interfaz. El 8000 del backend no se abre: la interfaz lo
    # alcanza por la red interna de Compose.
    if ! gcp compute firewall-rules describe "$REGLA" >/dev/null 2>&1; then
        paso "Abriendo el puerto 8080"
        gcp compute firewall-rules create "$REGLA" \
            --allow tcp:8080 \
            --target-tags "$ETIQUETA" \
            --description "Interfaz web de Logic Detective"
    fi

    paso "Esperando el arranque de la VM (Docker y swap)"
    for _ in $(seq 1 60); do
        if gcp compute ssh "$INSTANCIA" --zone "$ZONA" --quiet \
                --command "test -f /var/log/logic-detective-arranque-listo" >/dev/null 2>&1; then
            break
        fi
        sleep 10
    done
fi

# ---------------------------------------------------------------------------
#  Subir el código y levantar los contenedores
# ---------------------------------------------------------------------------
#  git archive manda exactamente lo commiteado: sin .venv, sin cachés y sin el
#  PDF del enunciado. Evita además tener que darle credenciales de GitHub a la
#  VM, porque el repositorio es privado.
paso "Subiendo el código"
PAQUETE="$(mktemp /tmp/logic-detective-XXXX.tar.gz)"
git -C "$RAIZ" archive --format=tar.gz HEAD > "$PAQUETE"
gcp compute scp "$PAQUETE" "$INSTANCIA:/tmp/logic-detective.tar.gz" --zone "$ZONA" --quiet
rm -f "$PAQUETE"

paso "Construyendo y levantando (en e2-micro el build tarda ~10 min)"
gcp compute ssh "$INSTANCIA" --zone "$ZONA" --quiet --command '
set -euo pipefail
sudo mkdir -p /opt/logic-detective
sudo tar xzf /tmp/logic-detective.tar.gz -C /opt/logic-detective
cd /opt/logic-detective

# Clave de sesión propia del despliegue. Se genera una sola vez y se conserva
# entre actualizaciones para no invalidar las investigaciones en curso.
if [ ! -f .env ]; then
    echo "SECRET_KEY=$(openssl rand -hex 32)" | sudo tee .env >/dev/null
fi

sudo docker compose up -d --build
sudo docker compose ps
'

paso "Listo"
echo "  Interfaz: http://$(ip_publica):8080"
echo
echo "  Al terminar la calificación:  ./deploy/desplegar-gcp.sh --eliminar"
