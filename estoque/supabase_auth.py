import json
import urllib.request
import urllib.error
import jwt
from jwt import PyJWKClient
from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from .models import Empresa, Perfil


_JWKS_CLIENT = None


def get_jwks_client():
    global _JWKS_CLIENT
    supabase_url = getattr(settings, 'SUPABASE_URL', '').rstrip('/')
    if not supabase_url:
        return None
    if _JWKS_CLIENT is None:
        jwks_url = f"{supabase_url}/auth/v1/.well-known/jwks.json"
        _JWKS_CLIENT = PyJWKClient(jwks_url, cache_keys=True)
    return _JWKS_CLIENT


def decode_supabase_jwt(raw_token):
    """
    Valida e decodifica um JWT emitido pelo Supabase Auth (ES256 via JWKS).
    """
    jwks_client = get_jwks_client()
    if not jwks_client:
        raise AuthenticationFailed("SUPABASE_URL não está configurado no servidor.")

    try:
        signing_key = jwks_client.get_signing_key_from_jwt(raw_token)
        payload = jwt.decode(
            raw_token,
            signing_key.key,
            algorithms=["ES256", "RS256"],
            audience="authenticated",
            options={"verify_exp": True},
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthenticationFailed("Sua sessão no Supabase expirou. Faça login novamente.")
    except jwt.InvalidTokenError as exc:
        raise AuthenticationFailed(f"Token do Supabase inválido: {str(exc)}")


def get_or_sync_django_user_from_supabase_payload(payload):
    """
    Localiza ou provisiona automaticamente o User e o Perfil do Django a partir
    dos claims autenticados do JWT do Supabase Auth.
    """
    email = (payload.get("email") or "").strip().lower()
    sub = payload.get("sub") or ""
    user_metadata = payload.get("user_metadata") or {}

    if not email and not sub:
        raise AuthenticationFailed("Token do Supabase não contém email ou identificador válido.")

    identificador = email or f"supabase_{sub[:30]}"

    user = (
        User.objects.filter(email__iexact=email).first()
        if email
        else None
    ) or User.objects.filter(username__iexact=identificador).first()

    with transaction.atomic():
        if not user:
            nome_completo = (
                user_metadata.get("nome")
                or user_metadata.get("full_name")
                or user_metadata.get("name")
                or identificador.split("@")[0]
            )
            partes = nome_completo.strip().split(" ", 1)
            primeiro_nome = partes[0][:150]
            sobrenome = (partes[1] if len(partes) > 1 else "")[:150]

            # Se ainda não houver nenhum superusuário/empresa cadastrada no banco,
            # o primeiro usuário autenticado via Supabase recebe perfil de GERENTE.
            empresa = Empresa.objects.first()
            eh_primeiro_acesso_sistema = False
            if not empresa:
                nome_empresa = user_metadata.get("empresa") or "CapFlow Bonelaria"
                empresa = Empresa.objects.create(nome_fantasia=nome_empresa)
                eh_primeiro_acesso_sistema = True

            cargo_meta = (user_metadata.get("cargo") or "").upper()
            cargos_validos = {c[0] for c in Perfil.TIPOS_CARGO}
            if cargo_meta in cargos_validos:
                cargo = cargo_meta
            elif eh_primeiro_acesso_sistema or not Perfil.objects.exists():
                cargo = "GERENTE"
            else:
                cargo = "OPERADOR"

            user = User.objects.create_user(
                username=identificador[:150],
                email=email,
                first_name=primeiro_nome,
                last_name=sobrenome,
            )
            user.set_unusable_password()
            user.save()

            Perfil.objects.create(
                usuario=user,
                empresa=empresa,
                cargo=cargo,
            )
        else:
            # Garante que o usuário existente possua um Perfil vinculado
            if not Perfil.objects.filter(usuario=user).exists():
                empresa = Empresa.objects.first()
                if not empresa:
                    empresa = Empresa.objects.create(nome_fantasia="CapFlow Bonelaria")
                cargo_meta = (user_metadata.get("cargo") or "GERENTE").upper()
                cargos_validos = {c[0] for c in Perfil.TIPOS_CARGO}
                cargo = cargo_meta if cargo_meta in cargos_validos else "GERENTE"
                Perfil.objects.create(usuario=user, empresa=empresa, cargo=cargo)

    user = User.objects.select_related("perfil", "perfil__empresa").get(pk=user.pk)
    if not user.is_active:
        raise AuthenticationFailed("Esta conta de usuário está inativa.")

    return user


class SupabaseJWTAuthentication(BaseAuthentication):
    """
    Autenticador DRF que aceita:
      - Authorization: Bearer <supabase_jwt>
      - Authorization: Token <supabase_jwt> (compatibilidade transparente com o app mobile)
    Se o token não for um JWT (3 partes separadas por '.'), retorna None para que
    o TokenAuthentication nativo do DRF processe normalmente (ex: nos testes locais).
    """

    def authenticate(self, request):
        auth = get_authorization_header(request).split()
        if not auth:
            return None

        prefix = auth[0].lower()
        if prefix not in (b"bearer", b"token"):
            return None

        if len(auth) != 2:
            raise AuthenticationFailed("Cabeçalho de autorização malformado.")

        try:
            raw_token = auth[1].decode("utf-8")
        except UnicodeError:
            raise AuthenticationFailed("Token contém caracteres inválidos.")

        # Um JWT sempre possui 3 segmentos separados por ponto (header.payload.signature).
        # Caso seja um token DRF de 40 caracteres hexadecimais, delega para TokenAuthentication.
        if raw_token.count(".") != 2:
            return None

        payload = decode_supabase_jwt(raw_token)
        user = get_or_sync_django_user_from_supabase_payload(payload)
        return (user, payload)


# =============================================================================
# CLIENTE REST DO SUPABASE AUTH (GoTrue)
# =============================================================================

def supabase_sign_in_with_password(identifier, password):
    """
    Autentica email e senha diretamente no Supabase Auth (/auth/v1/token?grant_type=password).
    Se o usuário digitar um username sem '@', resolve o email correspondente no banco.
    """
    supabase_url = getattr(settings, "SUPABASE_URL", "").rstrip("/")
    anon_key = getattr(settings, "SUPABASE_ANON_KEY", "")

    if not supabase_url or not anon_key:
        raise ValidationError({"erro": "Configuração do Supabase Auth ausente no servidor."})

    email = (identifier or "").strip()
    if "@" not in email:
        user_obj = User.objects.filter(username__iexact=email).first()
        if user_obj and user_obj.email:
            email = user_obj.email

    url = f"{supabase_url}/auth/v1/token?grant_type=password"
    body = json.dumps({"email": email, "password": password}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "apikey": anon_key,
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            err_data = json.loads(e.read().decode("utf-8"))
            msg = err_data.get("msg") or err_data.get("error_description") or "Credenciais inválidas no Supabase."
        except Exception:
            msg = "E-mail ou senha inválidos."
        raise AuthenticationFailed(msg)
    except urllib.error.URLError:
        raise ValidationError({"erro": "Não foi possível conectar ao servidor de autenticação do Supabase."})


def supabase_admin_create_or_update_user(email, password=None, user_metadata=None, ban_user=None):
    """
    Usa a SUPABASE_SERVICE_ROLE_KEY para criar ou atualizar um funcionário diretamente
    no Supabase Auth (com email_confirm=True para login imediato sem precisar confirmar link).
    """
    supabase_url = getattr(settings, "SUPABASE_URL", "").rstrip("/")
    service_key = getattr(settings, "SUPABASE_SERVICE_ROLE_KEY", "")

    if not supabase_url or not service_key:
        return None

    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
    }

    # Verifica se o usuário já existe no Supabase Auth
    list_req = urllib.request.Request(
        f"{supabase_url}/auth/v1/admin/users",
        headers=headers,
        method="GET",
    )
    existing_uid = None
    try:
        with urllib.request.urlopen(list_req, timeout=10) as res:
            data = json.loads(res.read().decode("utf-8"))
            for u in data.get("users", []):
                if (u.get("email") or "").lower() == email.lower():
                    existing_uid = u.get("id")
                    break
    except Exception:
        pass

    payload = {"email": email, "email_confirm": True}
    if password:
        payload["password"] = password
    if user_metadata:
        payload["user_metadata"] = user_metadata
    if ban_user is not None:
        payload["ban_duration"] = "876000h" if ban_user else "none"

    if existing_uid:
        req = urllib.request.Request(
            f"{supabase_url}/auth/v1/admin/users/{existing_uid}",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="PUT",
        )
    else:
        req = urllib.request.Request(
            f"{supabase_url}/auth/v1/admin/users",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            return json.loads(res.read().decode("utf-8"))
    except Exception:
        return None


def supabase_admin_delete_user(email):
    """
    Remove a conta do funcionário do Supabase Auth quando ele é excluído no painel.
    """
    supabase_url = getattr(settings, "SUPABASE_URL", "").rstrip("/")
    service_key = getattr(settings, "SUPABASE_SERVICE_ROLE_KEY", "")

    if not supabase_url or not service_key:
        return False

    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
    }

    try:
        list_req = urllib.request.Request(
            f"{supabase_url}/auth/v1/admin/users",
            headers=headers,
            method="GET",
        )
        with urllib.request.urlopen(list_req, timeout=10) as res:
            data = json.loads(res.read().decode("utf-8"))
            for u in data.get("users", []):
                if (u.get("email") or "").lower() == email.lower():
                    uid = u.get("id")
                    del_req = urllib.request.Request(
                        f"{supabase_url}/auth/v1/admin/users/{uid}",
                        headers=headers,
                        method="DELETE",
                    )
                    urllib.request.urlopen(del_req, timeout=10)
                    return True
    except Exception:
        pass
    return False
