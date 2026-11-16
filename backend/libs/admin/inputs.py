from decimal import Decimal

from pydantic import BaseModel

from libs.admin.types import AdminCreditLedgerSortType, AdminInviteSortType, AdminUserSortType
from libs.core.inputs import BasePageInput
from libs.permissions.types import RoleType


class AdminFindUserPageInput(BasePageInput):
    sort_by: AdminUserSortType  # ty: ignore[incompatible-mutable-override]


class AdminFindInvitePageInput(BasePageInput):
    sort_by: AdminInviteSortType  # ty: ignore[incompatible-mutable-override]


class AdminFindUserCreditLedgerPageInput(BasePageInput):
    sort_by: AdminCreditLedgerSortType  # ty: ignore[incompatible-mutable-override]


class AdminGrantUserCreditsInput(BaseModel):
    amount_usd: Decimal
    note: str


class AdminSetUserRoleInput(BaseModel):
    role: RoleType


class AdminSetUserActiveInput(BaseModel):
    is_active: bool


class AdminCreateInviteInput(BaseModel):
    name: str
    credit_amount_usd: Decimal
    note: str | None
    expires_in_days: int
