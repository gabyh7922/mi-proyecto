"""Bloque 2 — Escenarios sintéticos multi-turno.

Tres perfiles, cada uno diseñado para forzar un comportamiento del CAG:

- ``growing``: el proyecto crece turno a turno con requisitos coherentes. Mide la
  curva de coste y si el ``project_name`` original ("Nimbus") sobrevive al turno 20.
- ``pivot``: en el turno 5 el stack cambia (React Native -> Flutter). Mide si la
  metadata se actualiza limpiamente o si ``mentioned_technologies`` acumula ambas.
- ``contradiction``: el turno 3 fija el presupuesto en 30000 EUR, el turno 8 lo
  cambia a 80000. Mide cuál se preserva.

Cada turno declara un ``fact``: el "needle" (valor concreto) que las llamadas
posteriores deberían recordar. Ese tracker alimenta a ``MemoryDriftMetric``: en
el turno N se comprueba, para cada fact declarado en un turno k < N, si sigue
apareciendo en el snapshot (summary / anchors / metadata).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Turn:
    turn_index: int  # 1-based
    transcript: str
    fact: str  # valor que turnos posteriores deberían recordar


@dataclass(frozen=True)
class Scenario:
    name: str
    turns: list[Turn]

    def turns_through(self, n: int) -> list[Turn]:
        """Los primeros n turnos del escenario (para el sweep N in {1,3,6,10,20})."""
        return [t for t in self.turns if t.turn_index <= n]

    def facts_before(self, n: int) -> list[Turn]:
        """Facts declarados en turnos estrictamente anteriores a n (los que el
        turno n debería seguir recordando)."""
        return [t for t in self.turns if t.turn_index < n]


_GROWING = Scenario(
    name="growing",
    turns=[
        Turn(1, "We're building Nimbus, a web SaaS for warehouse inventory management. "
                "Stack: React, Node.js and PostgreSQL. Initial scope: product catalog CRUD.", "Nimbus"),
        Turn(2, "Add user authentication with email and password.", "authentication"),
        Turn(3, "Add multi-tenant support so each company has fully isolated data.", "multi-tenant"),
        Turn(4, "Add an audit log that records every change to stock levels.", "audit log"),
        Turn(5, "Add CSV export of inventory reports.", "CSV export"),
        Turn(6, "Integrate with Stripe for subscription billing.", "Stripe"),
        Turn(7, "Add role-based access control with admin, manager and viewer roles.", "role-based"),
        Turn(8, "Expose a REST API for third-party integrations.", "REST API"),
        Turn(9, "Add real-time stock alerts via email and Slack.", "Slack"),
        Turn(10, "Add a dashboard with charts of stock movements over time.", "dashboard"),
        Turn(11, "Support barcode scanning from mobile browsers.", "barcode"),
        Turn(12, "Add purchase order management.", "purchase order"),
        Turn(13, "Add a supplier management module.", "supplier"),
        Turn(14, "Add internationalization for English, Spanish and German.", "internationalization"),
        Turn(15, "Add two-factor authentication for admins.", "two-factor"),
        Turn(16, "Add automated data backup and restore.", "backup"),
        Turn(17, "Add a webhook system for stock events.", "webhook"),
        Turn(18, "Make the whole UI mobile-friendly and responsive.", "responsive"),
        Turn(19, "Add GDPR data export and deletion for end users.", "GDPR"),
        Turn(20, "Finalize: we need a full cost estimate for the entire Nimbus platform.", "Nimbus"),
    ],
)

_PIVOT = Scenario(
    name="pivot",
    turns=[
        Turn(1, "We're building Orion, a customer loyalty mobile app. "
                "Stack: React Native, Node.js and MongoDB.", "React Native"),
        Turn(2, "Add points accumulation and redemption.", "points"),
        Turn(3, "Add push notifications for promotions.", "push notifications"),
        Turn(4, "Add a referral program with reward codes.", "referral"),
        Turn(5, "Major change: we are dropping React Native and rebuilding the app in "
                "Flutter. The Node.js backend stays.", "Flutter"),
        Turn(6, "Add offline mode with local caching.", "offline"),
        Turn(7, "Add Apple Wallet and Google Wallet loyalty passes.", "Wallet"),
        Turn(8, "Add in-app chat support.", "chat"),
        Turn(9, "Add product analytics with Firebase.", "Firebase"),
        Turn(10, "Finalize the cost estimate for the Orion Flutter app.", "Flutter"),
    ],
)

_CONTRADICTION = Scenario(
    name="contradiction",
    turns=[
        Turn(1, "We're scoping Atlas, an internal HR tool. Stack: Vue, Django, PostgreSQL.", "Atlas"),
        Turn(2, "Add employee onboarding workflows.", "onboarding"),
        Turn(3, "The budget is fixed at 30000 EUR.", "30000"),
        Turn(4, "Add vacation request management.", "vacation"),
        Turn(5, "Add a reporting module for HR metrics.", "reporting"),
        Turn(6, "Add integration with the payroll provider.", "payroll"),
        Turn(7, "Add document storage for employment contracts.", "document"),
        Turn(8, "Correction: the budget is actually 80000 EUR, not 30000. Use 80000.", "80000"),
    ],
)

SCENARIOS: dict[str, Scenario] = {
    s.name: s for s in (_GROWING, _PIVOT, _CONTRADICTION)
}
