from pydantic import BaseModel
from pydantic import BaseModel, constr, condecimal
from typing import Optional

class TokenRequest(BaseModel):
    access_token: str


class ExpenseBase(BaseModel):
    amount: condecimal(gt=0, decimal_places=2)  # amount must be positive
    currency: Optional[constr(max_length=10)] = "USD"
    category: constr(max_length=50)
    description: Optional[constr(max_length=255)] = None

class ExpenseCreate(ExpenseBase):
    is_import: Optional[bool] = None
    processed_data_id: Optional[int] = None
    pass  # Same as base, used for creation

class ExpenseUpdate(BaseModel):
    amount: Optional[condecimal(gt=0, decimal_places=2)] = None
    currency: Optional[constr(max_length=10)] = None
    category: Optional[constr(max_length=50)] = None
    description: Optional[constr(max_length=255)] = None