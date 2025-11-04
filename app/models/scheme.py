from pydantic import BaseModel
from pydantic import BaseModel, constr, condecimal
from typing import Optional

class TokenRequest(BaseModel):
    access_token: str

class UpdateUserDetailsPayload(BaseModel):
    first_name : Optional[constr(max_length=255)] = None
    last_name : Optional[constr(max_length=255)] = None
    profile_image : Optional[constr(max_length=255)] = None
    country : Optional[constr(max_length=255)] = None
    locale : Optional[constr(max_length=255)] = None

    def to_dict(self) ->  dict:
        result =  {
            "first_name" : self.first_name,
            "last_name" : self.last_name,
            "profile_image" : self.profile_image,
            "country" : self.country,
            "locale" : self.locale
        }
        return result




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

    def to_dict(self) -> dict:
        data = {
            "amount": self.amount,
            "currency": self.currency,
            "category": self.category,
            "description": self.description
        }

        return data