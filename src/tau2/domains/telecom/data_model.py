import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import Field

from tau2.domains.telecom.utils import TELECOM_DB_PATH
from tau2.environment.db import DB
from tau2.utils.pydantic_utils import BaseModelNoExtra
from pydantic import ConfigDict
from tau2.environment.disk_dict import DiskList
from tau2.object_info import print_object_report
from tau2.utils import load_file

DEFAULT_START_DATE = datetime.date(2025, 1, 1)


class Address(BaseModelNoExtra):
    street: str = Field(description="Street address including house/apartment number")
    city: str = Field(description="City name")
    state: str = Field(description="State or province code (e.g., CA, NY)")
    zip_code: str = Field(description="Postal/ZIP code")


class Plan(BaseModelNoExtra):
    plan_id: str = Field(description="Unique identifier for the plan")
    name: str = Field(description="Display name of the plan")
    data_limit_gb: float = Field(description="Monthly data allowance in gigabytes (GB)")
    price_per_month: float = Field(description="Monthly price of the plan in USD")
    data_refueling_price_per_gb: float = Field(
        description="Price per gigabyte for data refueling"
    )


class DeviceType(str, Enum):
    PHONE = "phone"
    ROUTER = "router"
    TABLET = "tablet"
    WATCH = "watch"
    OTHER = "other"


class Device(BaseModelNoExtra):
    device_id: str = Field(description="Unique identifier for the device")
    device_type: DeviceType = Field(description="Type/category of the device")
    model: str = Field(description="Model name/number of the device")
    imei: Optional[str] = Field(
        None, description="International Mobile Equipment Identity number"
    )
    is_esim_capable: bool = Field(
        description="Whether the device supports eSIM technology"
    )
    activated: bool = Field(
        False, description="Whether the device has been activated on the network"
    )
    activation_date: Optional[datetime.datetime] = Field(
        None,
        description="Date and time when the device was activated (format: YYYY-MM-DDTHH:MM:SS, timezone: EST)",
    )
    last_esim_transfer_date: Optional[datetime.datetime] = Field(
        None,
        description="Last date an eSIM profile was transferred to this device (format: YYYY-MM-DDTHH:MM:SS, timezone: EST)",
    )


class LineStatus(str, Enum):
    ACTIVE = "Active"
    SUSPENDED = "Suspended"
    PENDING_ACTIVATION = "Pending Activation"
    CLOSED = "Closed"


class Line(BaseModelNoExtra):
    line_id: str = Field(description="Unique identifier for the line")
    phone_number: str = Field(description="Phone number associated with the line")
    status: LineStatus = Field(
        LineStatus.PENDING_ACTIVATION, description="Current status of the line"
    )
    plan_id: str = Field(description="Plan associated with this line")
    device_id: Optional[str] = Field(
        None, description="Device associated with this line"
    )
    data_used_gb: float = Field(
        0.0, description="Data used in the current billing cycle in gigabytes (GB)"
    )
    data_refueling_gb: float = Field(
        0.0, description="Data refueled in the current billing cycle in gigabytes (GB)"
    )
    roaming_enabled: bool = Field(
        False, description="Whether international roaming is enabled for this line"
    )
    contract_end_date: Optional[datetime.date] = Field(
        None,
        description="End date of the current contract, if applicable (format: YYYY-MM-DD, timezone: EST)",
    )
    last_plan_change_date: Optional[datetime.date] = Field(
        None,
        description="Date of the most recent plan change (format: YYYY-MM-DD, timezone: EST)",
    )
    last_sim_replacement_date: Optional[datetime.date] = Field(
        None,
        description="Date of the most recent SIM card replacement (format: YYYY-MM-DD, timezone: EST)",
    )
    suspension_start_date: Optional[datetime.date] = Field(
        None,
        description="Start date of the current suspension period, if applicable (format: YYYY-MM-DD, timezone: EST)",
    )


class LineItem(BaseModelNoExtra):
    description: str = Field(description="Descriptive text for the line item")
    amount: float = Field(
        description="Monetary amount in USD (positive for charges, negative for credits)"
    )
    date: datetime.date = Field(
        description="Date the line item was applied (format: YYYY-MM-DD, timezone: EST)"
    )
    item_type: str = Field(
        description="Category of the line item (e.g., Plan Charge, Overage, Fee, Credit, Payment)"
    )


class BillStatus(str, Enum):
    DRAFT = "Draft"
    ISSUED = "Issued"
    AWAITING_PAYMENT = "Awaiting Payment"
    PAID = "Paid"
    OVERDUE = "Overdue"
    DISPUTED = "Disputed"


class Bill(BaseModelNoExtra):
    bill_id: str = Field(description="Unique identifier for the bill")
    customer_id: str = Field(description="ID of the customer this bill belongs to")
    period_start: datetime.date = Field(
        description="Start date of the billing period (format: YYYY-MM-DD, timezone: EST)"
    )
    period_end: datetime.date = Field(
        description="End date of the billing period (format: YYYY-MM-DD, timezone: EST)"
    )
    issue_date: datetime.date = Field(
        description="Date the bill was issued/generated (format: YYYY-MM-DD, timezone: EST)"
    )
    total_due: float = Field(description="Total amount due in USD")
    due_date: datetime.date = Field(
        description="Date by which payment is due (format: YYYY-MM-DD, timezone: EST)"
    )
    line_items: List[LineItem] = Field(
        default_factory=list,
        description="Individual charges, credits, and payments on this bill",
    )
    status: BillStatus = Field(
        BillStatus.DRAFT, description="Current status of the bill"
    )


class AccountStatus(str, Enum):
    ACTIVE = "Active"
    SUSPENDED = "Suspended"
    PENDING_VERIFICATION = "Pending Verification"
    CLOSED = "Closed"


class PaymentMethodType(str, Enum):
    CREDIT_CARD = "Credit Card"
    DEBIT_CARD = "Debit Card"
    PAYPAL = "PayPal"


class PaymentMethod(BaseModelNoExtra):
    method_type: PaymentMethodType = Field(description="Type of payment method")
    account_number_last_4: str = Field(
        description="Last 4 digits of the account number"
    )
    expiration_date: str = Field(
        description="The expiration date of the payment method in the format MM/YYYY"
    )


class Customer(BaseModelNoExtra):
    customer_id: str = Field(description="Unique identifier for the customer")
    full_name: str = Field(description="Customer's full name")
    date_of_birth: str = Field(
        description="Customer's date of birth for identity verification (format: YYYY-MM-DD)"
    )
    email: str = Field(description="Customer's email address")
    phone_number: str = Field(description="Customer's primary contact phone number")
    address: Address = Field(description="Customer's billing address")
    account_status: AccountStatus = Field(
        AccountStatus.PENDING_VERIFICATION,
        description="Current status of the customer account",
    )
    payment_methods: List[PaymentMethod] = Field(
        default_factory=list, description="Stored payment methods for this customer"
    )
    line_ids: List[str] = Field(
        default_factory=list, description="Phone/data lines owned by this customer"
    )
    bill_ids: List[str] = Field(
        default_factory=list, description="Bills associated with this customer"
    )
    created_at: datetime.datetime = Field(
        DEFAULT_START_DATE,
        description="Date and time when the customer account was created (format: YYYY-MM-DDTHH:MM:SS, timezone: EST)",
    )
    last_extension_date: Optional[datetime.date] = Field(
        None,
        description="Date of the most recent payment extension (used for quarterly limit check) (format: YYYY-MM-DD, timezone: EST)",
    )
    goodwill_credit_used_this_year: float = Field(
        0.0, description="Amount of goodwill credit used in the current calendar year"
    )


class TelecomDB(DB):
    """Database interface for telecom domain."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    plans: Any = Field(
        default_factory=list, description="Available service plans"
    )
    customers: Any = Field(
        default_factory=list, description="All customers in the system"
    )
    lines: Any = Field(
        default_factory=list, description="All lines in the system"
    )
    bills: Any = Field(
        default_factory=list, description="All bills in the system"
    )
    devices: Any = Field(
        default_factory=list, description="All devices in the system"
    )

    def get_statistics(self) -> Dict[str, Any]:
        """Get the statistics of the database."""
        num_plans = len(self.plans)
        num_customers = len(self.customers)
        num_lines = len(self.lines)
        num_bills = len(self.bills)
        num_devices = len(self.devices)
        num_payment_methods = sum(
            len(customer.payment_methods) for customer in self.customers
        )

        return {
            "num_plans": num_plans,
            "num_customers": num_customers,
            "num_lines": num_lines,
            "num_bills": num_bills,
            "num_devices": num_devices,
            "num_payment_methods": num_payment_methods,
        }


    @classmethod
    def load(cls, path: str, in_memory: bool = False) -> "TelecomDB":
        if in_memory:
            sqlite_path = f"{path}.sqlite"
            
            plans_list = DiskList(sqlite_path, "plans", Plan)
            customers_list = DiskList(sqlite_path, "customers", Customer)
            lines_list = DiskList(sqlite_path, "lines", Line)
            bills_list = DiskList(sqlite_path, "bills", Bill)
            devices_list = DiskList(sqlite_path, "devices", Device)

            if len(plans_list) == 0 and len(customers_list) == 0 and len(lines_list) == 0:
                data = load_file(path)
                    
                for plan_data in data.get("plans", []):
                    plans_list.append(Plan.model_validate(plan_data))
                for cust_data in data.get("customers", []):
                    customers_list.append(Customer.model_validate(cust_data))
                for line_data in data.get("lines", []):
                    lines_list.append(Line.model_validate(line_data))
                for bill_data in data.get("bills", []):
                    bills_list.append(Bill.model_validate(bill_data))
                for dev_data in data.get("devices", []):
                    devices_list.append(Device.model_validate(dev_data))

            return cls.model_construct(
                plans=plans_list,
                customers=customers_list,
                lines=lines_list,
                bills=bills_list,
                devices=devices_list,
            )
        else:
            data = load_file(path)
            
            data["plans"] = [Plan.model_validate(d) for d in data.get("plans", [])]
            data["customers"] = [Customer.model_validate(d) for d in data.get("customers", [])]
            data["lines"] = [Line.model_validate(d) for d in data.get("lines", [])]
            data["bills"] = [Bill.model_validate(d) for d in data.get("bills", [])]
            data["devices"] = [Device.model_validate(d) for d in data.get("devices", [])]
            return cls.model_construct(**data)


def get_db(in_memory: bool = False):
    """Get an instance of the telecom database."""
    return TelecomDB.load(TELECOM_DB_PATH, in_memory=in_memory)


if __name__ == "__main__":
    db = get_db(True)
    print_object_report(db, "TelecomDB")
    db = get_db(False)
    print_object_report(db, "TelecomDB")
    print(db.get_statistics())
