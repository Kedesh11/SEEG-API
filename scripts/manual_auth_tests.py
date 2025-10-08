#!/usr/bin/env python3
"""Tests manuels de tous les endpoints d'authentification.

Le script enchaîne les appels vers l'API d'auth et affiche un résumé.
Tous les paramètres (URL et identifiants) sont configurables via des
variables d'environnement pour permettre des tests en préproduction ou
en production selon les besoins.
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple

import httpx


DEFAULT_BASE_URL = "http://localhost:8000/api/v1"


def env(name: str, default: str) -> str:
    """Récupère une variable d'environnement avec une valeur par défaut."""
    return os.getenv(name, default)


BASE_URL = env("API_BASE_URL", DEFAULT_BASE_URL).rstrip("/")

ADMIN_EMAIL = env("ADMIN_EMAIL", "sevankedesh11@gmail.com")
ADMIN_PASSWORD = env("ADMIN_PASSWORD", "Sevan@Seeg")

RECRUITER_EMAIL = env("RECRUITER_EMAIL", "recruteur@test.local")
RECRUITER_PASSWORD = env("RECRUITER_PASSWORD", "Recrut3ur#2025")

DEFAULT_CANDIDATE_EMAIL = env("CANDIDATE_EMAIL", "candidate@test.local")
DEFAULT_CANDIDATE_PASSWORD = env("CANDIDATE_PASSWORD", "Password#2025")
DEFAULT_CANDIDATE_MATRICULE = int(env("CANDIDATE_MATRICULE", "123456"))


def build_candidate_email() -> str:
    """Génère un email unique pour éviter les collisions si besoin."""
    base = DEFAULT_CANDIDATE_EMAIL
    if base == "candidate@test.local":
        timestamp = int(time.time())
        return f"candidate.{timestamp}@test.local"
    return base


@dataclass
class StepResult:
    name: str
    status_code: int
    success: bool
    detail: str = ""
    data: Optional[Dict[str, object]] = None


@dataclass
class AuthTestContext:
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    admin_token: Optional[str] = None
    recruiter_token: Optional[str] = None
    candidate_email: str = field(default_factory=build_candidate_email)
    candidate_password: str = DEFAULT_CANDIDATE_PASSWORD


def pretty_json(data: Dict[str, object]) -> str:
    try:
        return json.dumps(data, ensure_ascii=False, indent=2)
    except Exception:
        return str(data)


def run_step(
    client: httpx.Client,
    name: str,
    method: str,
    path: str,
    *,
    expected_status: Iterable[int] = (200,),
    headers: Optional[Dict[str, str]] = None,
    **request_kwargs: object,
) -> StepResult:
    url = f"{BASE_URL}{path}"
    try:
        response = client.request(method, url, headers=headers, **request_kwargs)
    except httpx.HTTPError as exc:
        return StepResult(name=name, status_code=-1, success=False, detail=str(exc))

    success = response.status_code in tuple(expected_status)
    detail = response.text.strip()
    data: Optional[Dict[str, object]] = None
    try:
        data = response.json()
    except Exception:
        pass

    return StepResult(
        name=name,
        status_code=response.status_code,
        success=success,
        detail=detail,
        data=data,
    )


def bearer(token: Optional[str]) -> Dict[str, str]:
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def main() -> int:
    print(f"✔ Point de départ API : {BASE_URL}")

    ctx = AuthTestContext()
    results: List[StepResult] = []

    timeout = httpx.Timeout(30.0, connect=30.0)
    with httpx.Client(timeout=timeout, headers={"content-type": "application/json"}) as client:
        # 1. Créer le premier admin
        results.append(
            run_step(
                client,
                "create_first_admin",
                "POST",
                "/auth/create-first-admin",
                expected_status=(200, 400),
            )
        )

        # 2. Connexion admin
        admin_login = run_step(
            client,
            "admin_login",
            "POST",
            "/auth/login",
            expected_status=(200, 401),
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        )
        results.append(admin_login)
        if admin_login.success and admin_login.data:
            ctx.admin_token = admin_login.data.get("access_token")

        # 3. Création/connexion recruteur
        if ctx.admin_token:
            create_recruiter = run_step(
                client,
                "create_recruiter",
                "POST",
                "/auth/create-user",
                expected_status=(200, 400),
                headers={**bearer(ctx.admin_token)},
                json={
                    "email": RECRUITER_EMAIL,
                    "password": RECRUITER_PASSWORD,
                    "first_name": "Jean",
                    "last_name": "Mavoungou",
                    "role": "recruiter",
                },
            )
            results.append(create_recruiter)

            recruiter_login = run_step(
                client,
                "recruiter_login",
                "POST",
                "/auth/login",
                expected_status=(200,),
                json={"email": RECRUITER_EMAIL, "password": RECRUITER_PASSWORD},
            )
            results.append(recruiter_login)
            if recruiter_login.success and recruiter_login.data:
                ctx.recruiter_token = recruiter_login.data.get("access_token")

        # 4. Signup candidat (peut renvoyer 400 si doublon)
        candidate_payload = {
            "email": ctx.candidate_email,
            "password": ctx.candidate_password,
            "first_name": "Ada",
            "last_name": "Lovelace",
            "matricule": DEFAULT_CANDIDATE_MATRICULE,
            "phone": "+24106223344",
            "date_of_birth": "1990-01-01",
            "sexe": "F",
        }

        results.append(
            run_step(
                client,
                "candidate_signup",
                "POST",
                "/auth/signup",
                expected_status=(200, 400),
                json=candidate_payload,
            )
        )

        # 5. Connexion candidat
        candidate_login = run_step(
            client,
            "candidate_login",
            "POST",
            "/auth/login",
            expected_status=(200,),
            json={"email": ctx.candidate_email, "password": ctx.candidate_password},
        )
        results.append(candidate_login)
        if candidate_login.success and candidate_login.data:
            ctx.access_token = candidate_login.data.get("access_token")
            ctx.refresh_token = candidate_login.data.get("refresh_token")

        # 6. Profil courant
        results.append(
            run_step(
                client,
                "get_me",
                "GET",
                "/auth/me",
                headers={**bearer(ctx.access_token)},
            )
        )

        # 7. Vérification matricule
        results.append(
            run_step(
                client,
                "verify_matricule",
                "GET",
                "/auth/verify-matricule",
                headers={**bearer(ctx.access_token)},
            )
        )

        # 8. Refresh token
        if ctx.refresh_token:
            refresh_result = run_step(
                client,
                "refresh_token",
                "POST",
                "/auth/refresh",
                json={"refresh_token": ctx.refresh_token},
            )
            results.append(refresh_result)
            if refresh_result.success and refresh_result.data:
                ctx.access_token = refresh_result.data.get("access_token", ctx.access_token)
                ctx.refresh_token = refresh_result.data.get("refresh_token", ctx.refresh_token)

        # 9. Changement de mot de passe (candidat)
        results.append(
            run_step(
                client,
                "change_password",
                "POST",
                "/auth/change-password",
                headers={**bearer(ctx.access_token)},
                json={
                    "current_password": ctx.candidate_password,
                    "new_password": ctx.candidate_password + "!",
                },
            )
        )

        # 10. Demande de reset mot de passe
        results.append(
            run_step(
                client,
                "forgot_password",
                "POST",
                "/auth/forgot-password",
                json={"email": ctx.candidate_email},
            )
        )

        # 11. Déconnexion
        results.append(
            run_step(
                client,
                "logout",
                "POST",
                "/auth/logout",
                headers={**bearer(ctx.access_token)},
            )
        )

    print("\n=== Résultats détaillés ===")
    for step in results:
        header = f"[{step.name}] status={step.status_code} success={'oui' if step.success else 'non'}"
        print(header)
        if step.data:
            print(pretty_json(step.data))
        elif step.detail:
            print(step.detail)
        print("-" * 60)

    failures = [s for s in results if not s.success]
    print("\n=== Résumé ===")
    print(f"Total étapes : {len(results)}")
    print(f"Réussites   : {len(results) - len(failures)}")
    print(f"Échecs      : {len(failures)}")

    if failures:
        print("\nÉtapes en échec :")
        for step in failures:
            print(f"- {step.name} (status {step.status_code})")

    print("\nAstuce : un status 400 sur create_first_admin ou candidate_signup indique souvent qu'une entrée existe déjà (comportement attendu).")

    return 0 if not failures else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("Interruption utilisateur.")
        raise SystemExit(130)

