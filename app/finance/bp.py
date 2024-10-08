from flask import jsonify, request
from flask.views import MethodView
from flask_smorest import Blueprint
from sqlalchemy import Date, and_, cast, func, or_

from app.base import session
from app.choices import AccountCategories, Statuses
from app.finance.models import (
    AttachedFile,
    BalanceAccount,
    CashRegister,
    Counterparty,
    PaymentType,
    TaxRate,
    Transaction,
    TransactionComment,
    tax_rate_payment_type,
)
from app.finance.schema import (
    AttachedFileSchema,
    BalanceAccountCreateSchema,
    BalanceAccountRetrieveSchema,
    BalanceAccountUpdateSchema,
    ByNameAndCategorySearchSchema,
    ByNameSearchSchema,
    CashRegisterCreateSchema,
    CashRegisterRetrieveSchema,
    CashRegisterUpdateSchema,
    CounterpartyArgsSchema,
    CounterpartyForTransaction,
    CounterpartyRetrieveSchema,
    CounterpartySchema,
    CounterpartyUpdateSchema,
    PagBalanceAccountSchema,
    PagCashRegisterSchema,
    PagCounterpartySchema,
    PagPaymentTypeSchema,
    PagTaxRateSchema,
    PagTransactionSchema,
    PaymentTypeCreateSchema,
    PaymentTypeRetrieveUpdateSchema,
    TaxRateArgsSchema,
    TaxRateCreateSchema,
    TaxRateRetrieveSchema,
    TaxRateUpdateSchema,
    TransactionArgsSchema,
    TransactionCommentCreateSchema,
    TransactionCreateUpdateSchema,
    TransactionRetrieveSchema,
)
from app.finance.utils import TRANSACTION_DEBIT_CREDIT_CATEGORIES
from app.user.models import Salary
from app.utils.func import hash_image_save, sql_exception_handler, token_required
from app.utils.mixins import CustomMethodPaginationView
from app.utils.schema import ResponseSchema

finance = Blueprint(
    "finance", __name__, url_prefix="/finance", description="operations on finance"
)


@finance.route("/payment_type")
class PaymentTypeView(CustomMethodPaginationView):
    model = PaymentType

    @finance.arguments(ByNameSearchSchema, location="query")
    @finance.response(400, ResponseSchema)
    @finance.response(200, PagPaymentTypeSchema)
    @token_required
    def get(c, self, args):
        """List PaymentType"""
        return super(PaymentTypeView, self).get(args)

    @token_required
    @sql_exception_handler
    @finance.arguments(PaymentTypeCreateSchema)
    @finance.response(400, ResponseSchema)
    @finance.response(201, PaymentTypeCreateSchema)
    def post(c, self, new_data):
        """Add a new payment_type"""

        payment_type = PaymentType(**new_data)
        session.add(payment_type)
        session.flush()
        # если has_commissioner == True то создастся новый контрагент
        payment_type.create_counterparty()
        session.commit()
        new_data["id"] = payment_type.id
        return new_data


@finance.route("/payment_type/<int:id>")
class PaymentTypeByIdView(MethodView):
    @token_required
    @finance.response(200, PaymentTypeRetrieveUpdateSchema)
    def get(c, self, id):
        """Get payment_type by ID"""

        item = PaymentType.get_or_404(id)

        return item

    @token_required
    @sql_exception_handler
    @finance.arguments(PaymentTypeRetrieveUpdateSchema)
    @finance.response(200, PaymentTypeRetrieveUpdateSchema)
    def put(c, self, update_data, id):
        """Update existing payment_type"""
        item = PaymentType.get_or_404(id)

        for col, val in update_data.items():
            setattr(item, col, val)
        item.create_counterparty()
        item.update_counterparty(update_data.get("name"))
        session.merge(item)
        session.commit()

        return item

    @token_required
    @sql_exception_handler
    @finance.response(204)
    def delete(c, self, id):
        """Delete payment_type"""
        payment_type = PaymentType.get_or_404(id)
        session.delete(payment_type)
        session.commit()


@finance.route("/cash_register")
class CashRegisterView(CustomMethodPaginationView):
    model = CashRegister

    @token_required
    @sql_exception_handler
    @finance.arguments(CashRegisterCreateSchema)
    @finance.response(400, ResponseSchema)
    @finance.response(201, CashRegisterCreateSchema)
    def post(c, self, new_data):
        """Add a new cash_register"""
        payment_types_ids = new_data.pop("payment_types_ids")
        payment_types = PaymentType.query.filter(
            PaymentType.id.in_(payment_types_ids)
        ).all()
        new_data["payment_types"] = payment_types

        cash_register = CashRegister(**new_data)
        schema = CashRegisterCreateSchema()
        cash_register.add_temp_data("history_data", schema.dump(cash_register))
        session.add(cash_register)
        session.commit()
        schema = CashRegisterCreateSchema()
        return schema.dump(cash_register), 201

    @finance.arguments(ByNameSearchSchema, location="query")
    @finance.response(400, ResponseSchema)
    @finance.response(200, PagCashRegisterSchema)
    @token_required
    def get(c, self, args):
        """List cash_register"""
        return super(CashRegisterView, self).get(args)


@finance.route("/cash_register/<int:id>")
class CashRegisterByIdView(MethodView):
    @token_required
    @finance.response(200, CashRegisterRetrieveSchema)
    def get(c, self, id):
        """Get cash_register by ID"""

        item = CashRegister.get_or_404(id)
        return item

    @token_required
    @sql_exception_handler
    @finance.arguments(CashRegisterUpdateSchema)
    @finance.response(200, CashRegisterUpdateSchema)
    def put(c, self, update_data, id):
        """Update existing cash_register"""
        payment_types_ids = update_data.pop("payment_types_ids", None)
        if payment_types_ids:
            payment_types = PaymentType.query.filter(
                PaymentType.id.in_(payment_types_ids)
            ).all()
            update_data["payment_types"] = payment_types
        item = CashRegister.get_or_404(id)

        # delete all payment types from object
        item.payment_types.clear()
        schema = CashRegisterUpdateSchema()
        item.add_temp_data("history_data", schema.dump(item))

        for col, val in update_data.items():
            setattr(item, col, val)
        session.merge(item)
        session.commit()

        return schema.dump(item)

    @token_required
    @sql_exception_handler
    @finance.response(204)
    def delete(c, self, id):
        """Delete cash_register"""
        CashRegister.delete_with_get(id)


@finance.route("/balance_account")
class BalanceAccountView(CustomMethodPaginationView):
    model = BalanceAccount

    @finance.arguments(ByNameAndCategorySearchSchema, location="query")
    @finance.response(400, ResponseSchema)
    @finance.response(200, PagBalanceAccountSchema)
    @token_required
    def get(c, self, args):
        """get list balance_account"""
        category = args.pop("category", None)
        _type = args.pop("type", None)
        lst = []
        if category:
            lst.append(self.model.category == category)
        if _type:
            lst.append(self.model.account_type == _type)
        return super(BalanceAccountView, self).get(args, query_args=lst)

    @token_required
    @sql_exception_handler
    @finance.arguments(BalanceAccountCreateSchema)
    @finance.response(400, ResponseSchema)
    @finance.response(201, BalanceAccountCreateSchema)
    def post(c, self, new_data):
        """Add a new balance_account"""

        balance_account = BalanceAccount(**new_data, category=AccountCategories.USER)
        session.add(balance_account)
        session.commit()
        new_data["id"] = balance_account.id
        return new_data


@finance.route("/balance_account/<int:id>")
class BalanceAccountByIdView(MethodView):
    @token_required
    @finance.response(200, BalanceAccountRetrieveSchema)
    def get(c, self, id):
        """Get balance_account by ID"""

        item = BalanceAccount.get_or_404(id)

        return item

    @token_required
    @sql_exception_handler
    @finance.arguments(BalanceAccountUpdateSchema)
    @finance.response(200, BalanceAccountUpdateSchema)
    def put(c, self, update_data, id):
        """Update existing balance_account"""

        item = BalanceAccount.get_or_404(id)
        if item.category == AccountCategories.SYSTEM:
            return (
                jsonify(
                    {
                        "message": "You can not edit BalanceAccount with category == SYSTEM!"
                    }
                ),
                403,
            )

        for col, val in update_data.items():
            setattr(item, col, val)
        session.merge(item)
        session.commit()
        return item

    @token_required
    @sql_exception_handler
    @finance.response(204)
    def delete(c, self, id):
        """Delete balance_account"""
        item = BalanceAccount.get_or_404(id)
        if item.category == AccountCategories.SYSTEM:
            return (
                jsonify(
                    {
                        "message": "You can not delete BalanceAccount with category == SYSTEM!"
                    }
                ),
                400,
            )
        session.delete(item)
        session.commit()


@finance.route("/get_transaction_categories")
def get_transaction_categories():
    return jsonify(TRANSACTION_DEBIT_CREDIT_CATEGORIES)


@finance.route("/transaction")
class TransactionView(CustomMethodPaginationView):
    model = Transaction

    @finance.arguments(TransactionArgsSchema, location="query")
    @finance.response(400, ResponseSchema)
    @finance.response(200, PagTransactionSchema)
    @token_required
    def get(c, self, args):
        """get list transaction"""

        search_term: str = args.pop("search", None)
        created_date = args.pop("created_date", None)
        status = args.pop("status", None)
        category_name = args.pop("category_name", None)
        category_object_id = args.pop("category_object_id", None)
        category = args.pop("category", None)
        start_date = args.pop("start_date", None)
        end_date = args.pop("end_date", None)
        custom_query = None
        lst = []

        if category:
            lst.append(self.model.category == category)

        if start_date and end_date:
            lst.append(cast(self.model.created_at, Date).between(start_date, end_date))

        # если в качестве категории будет Юзер то нужно его поменять на Salary
        # потому что в ней баланс юзера
        if category_name == "User":
            category_name = "Salary"
            category_object_id = (
                Salary.query.filter_by(user_id=category_object_id).first().id
            )

        if search_term:
            lst.append(
                or_(
                    Transaction.debit_name.ilike(f"%{search_term}%"),
                    Transaction.credit_name.ilike(f"%{search_term}%"),
                )
            )

        if created_date:
            lst.append(func.date(self.model.created_at) == created_date)
        if status:
            lst.append(self.model.status == status)
        if category_name and category_object_id:
            custom_query = Transaction.query.filter(
                or_(
                    Transaction.debit_content_type == category_name,
                    Transaction.credit_content_type == category_name,
                )
            ).filter(
                or_(
                    Transaction.debit_object_id == category_object_id,
                    Transaction.credit_object_id == category_object_id,
                )
            )
        return super(TransactionView, self).get(
            args, query_args=lst, custom_query=custom_query
        )

    @token_required
    @sql_exception_handler
    @finance.arguments(TransactionCreateUpdateSchema)
    @finance.response(400, ResponseSchema)
    @finance.response(201, TransactionCreateUpdateSchema)
    def post(c, self, new_data):
        """Add a new transaction"""
        new_data["credit_content_type"] = new_data.pop("credit_category")
        new_data["debit_content_type"] = new_data.pop("debit_category")
        credit_name = (
            session.query(globals()[new_data["credit_content_type"]])
            .get(new_data["credit_object_id"])
            .name
        )
        debit_name = (
            session.query(globals()[new_data["debit_content_type"]])
            .get(new_data["debit_object_id"])
            .name
        )
        transaction = Transaction(
            **new_data,
            category=AccountCategories.USER,
            credit_name=credit_name,
            debit_name=debit_name,
        )
        transaction.add_temp_data("history_data", transaction.format())
        session.add(transaction)
        transaction.publish()
        session.commit()
        new_data["id"] = transaction.id
        return new_data


@finance.get("/get_counterparties_for_transaction")
def get_counterparties_for_transaction():
    """Get Counterparties with status == ON For Transaction
    when assigning Credit or Debit
    """
    counterparties = Counterparty.query.filter(Counterparty.status == Statuses.ON)
    schema = CounterpartyForTransaction()
    return schema.dump(counterparties, many=True)


@finance.put("/cancel_transaction/<int:id>")
@sql_exception_handler
@token_required
def cancel_transaction(c, id):
    """cancel Transaction if it published"""
    item: Transaction = Transaction.get_or_404(id)

    if not item.can_cancel:
        return jsonify({"message": "Can not change to Cancelled!"}), 400

    item.cancel()
    item.add_temp_data("history_data", item.format())
    session.commit()
    return jsonify(
        {
            "message": "success",
        }
    )


@finance.route("/transaction/<int:id>")
class TransactionByIdView(MethodView):
    @token_required
    @finance.response(200, TransactionRetrieveSchema)
    def get(c, self, id):
        """Get transaction by ID"""

        item = Transaction.get_or_404(id)

        return item

    @token_required
    @sql_exception_handler
    @finance.arguments(TransactionCreateUpdateSchema)
    @finance.response(200, TransactionCreateUpdateSchema)
    def put(c, self, update_data, id):
        """Update existing Transaction"""

        item = Transaction.get_or_404(id)
        update_data["credit_content_type"] = update_data.pop("credit_category")
        update_data["debit_content_type"] = update_data.pop("debit_category")
        if not item.can_edit:
            return (
                jsonify(
                    {
                        "message": "You can not edit transaction with status <PUBLISHED or CANCELLED>!"
                    }
                ),
                400,
            )
        for col, val in update_data.items():
            setattr(item, col, val)
        item.publish()
        item.add_temp_data("history_data", item.format())
        session.merge(item)
        session.commit()
        return item


@finance.post("/create_comment/<int:transaction_id>")
@finance.arguments(TransactionCommentCreateSchema)
@finance.response(201, TransactionCommentCreateSchema)
@sql_exception_handler
@token_required
def create_comment(
    c,
    new_data,
    transaction_id,
):
    """Create Comment For Transaction"""
    item = TransactionComment(
        **new_data,
        transaction_id=transaction_id,
        user_id=c.id,
        user_full_name=c.full_name,
    )

    session.add(item)
    session.commit()
    schema = TransactionCommentCreateSchema()

    return schema.dump(item)


@finance.route("/counterparty")
class CounterpartyView(CustomMethodPaginationView):
    model = Counterparty

    @finance.arguments(CounterpartyArgsSchema, location="query")
    @finance.response(400, ResponseSchema)
    @finance.response(200, PagCounterpartySchema)
    @token_required
    def get(c, self, args):
        """get list counterparty"""
        created_date = args.pop("created_date", None)
        category = args.pop("category", None)
        status = args.pop("status", None)
        lst = []

        if created_date:
            lst.append(func.date(self.model.created_at) == created_date)
        if category:
            lst.append(self.model.category == category)
        if status:
            lst.append(self.model.status == status)

        return super(CounterpartyView, self).get(args, query_args=lst)

    @token_required
    # @sql_exception_handler
    @finance.arguments(CounterpartySchema)
    @finance.response(400, ResponseSchema)
    @finance.response(201, CounterpartySchema)
    def post(c, self, new_data):
        """Add a new counterparty"""
        counterparty = Counterparty(**new_data, category=AccountCategories.USER)
        session.add(counterparty)
        counterparty.add_temp_data("history_data", counterparty)
        session.commit()
        return counterparty


@finance.route("/counterparty/<int:id>")
class CounterPartyByIdView(MethodView):
    @token_required
    @finance.response(200, CounterpartyRetrieveSchema)
    def get(c, self, id):
        """Get counterparty by ID"""

        item = Counterparty.get_or_404(id)
        return item

    @token_required
    @sql_exception_handler
    @finance.arguments(CounterpartyUpdateSchema)
    @finance.response(200, CounterpartyUpdateSchema)
    def put(c, self, update_data, id):
        """Update existing counterparty"""

        item = Counterparty.get_or_404(id)
        if not item.can_delete_and_edit:
            return (
                jsonify(
                    {"message": "You can not edit counterparty with category <SYSTEM>!"}
                ),
                400,
            )

        for col, val in update_data.items():
            setattr(item, col, val)
        schema = CounterpartyUpdateSchema()
        item.add_temp_data("history_data", schema.dump(item))
        session.merge(item)
        session.commit()
        return item

    @token_required
    @sql_exception_handler
    @finance.response(204)
    def delete(c, self, id):
        """Delete counterparty"""
        counterparty = Counterparty.get_or_404(id)
        if counterparty.can_delete_and_edit:
            session.delete(counterparty)
            session.commit()
        else:
            return (
                jsonify(
                    {
                        "message": "You can not delete counterparty with category <SYSTEM>!"
                    }
                ),
                400,
            )


@finance.route("/attached_file/<int:id>/")
class AttachedFileView(MethodView):
    @finance.response(400, ResponseSchema)
    @finance.response(200, AttachedFileSchema)
    @token_required
    def get(c, self, id):

        documents = AttachedFile.get_or_404(id)
        return documents

    @sql_exception_handler
    @finance.arguments(AttachedFileSchema, location="form")
    @finance.response(400, ResponseSchema)
    @finance.response(200, AttachedFileSchema)
    @token_required
    def put(c, self, update_data, id):
        """update file for counter_party

        ВАЖНО: Swagger UI некорректно обрабатывает загрузку файлов
        через 'multipart/form-data'.
        Для отправки файла используйте Postman или другой инструмент,
        поддерживающий отправку файлов через форму.
        Обязательно передавайте файл в поле 'file', и укажите остальные параметры,
        такие как 'filename' и 'description'.
        """
        file = request.files.get("file", None)
        if not file:
            return jsonify({"message": "file field is required!"}), 400
        counterparty_id = update_data.get("counterparty_id")

        path = hash_image_save(
            uploaded_file=file, model_name="counterparty", ident=counterparty_id
        )
        update_data["filepath"] = path
        file = AttachedFile.get_or_404(id)

        for col, val in update_data.items():
            setattr(file, col, val)

        session.merge(file)
        session.commit()
        return file

    @token_required
    @sql_exception_handler
    @finance.response(204)
    def delete(c, self, id):
        """Delete attached_file"""
        AttachedFile.delete_with_get(id)


@finance.post("/attached_file")
@token_required
@sql_exception_handler
@finance.arguments(AttachedFileSchema, location="form")
@finance.response(200, AttachedFileSchema)
def create_attach_file(c, new_data):
    """
    Add a new attached_file to a counterparty

     ВАЖНО: Swagger UI некорректно обрабатывает загрузку файлов
     через 'multipart/form-data'.
     Для отправки файла используйте Postman или другой инструмент,
     поддерживающий отправку файлов через форму.
     Обязательно передавайте файл в поле 'file', и укажите остальные параметры,
     такие как 'filename' и 'description'.
    """
    file = request.files.get("file", None)
    if not file:
        return jsonify({"message": "file field is required!"}), 400
    counterparty_id = new_data.get("counterparty_id")
    path = hash_image_save(
        uploaded_file=file, model_name="counterparty", ident=counterparty_id
    )
    item = AttachedFile(**new_data, filepath=path)

    session.add(item)
    session.commit()
    new_data["id"] = item.id
    new_data["filepath"] = path
    return new_data


@finance.route("/tax_rate")
class TaxRateView(CustomMethodPaginationView):
    model = TaxRate

    @finance.arguments(TaxRateArgsSchema, location="query")
    @finance.response(400, ResponseSchema)
    @finance.response(200, PagTaxRateSchema)
    @token_required
    def get(c, self, args):
        """get list tax_rate"""
        category = args.pop("category", None)
        status = args.pop("status", None)
        payment_type_name = args.pop("payment_type_name", None)
        lst = []
        custom_query = None
        if category:
            lst.append(self.model.category == category)
        if payment_type_name:
            custom_query = (
                session.query(TaxRate)
                .join(tax_rate_payment_type)
                .join(PaymentType)
                .filter(PaymentType.name == payment_type_name)
                .order_by(TaxRate.created_at.desc())
            )
        if status:
            lst.append(self.model.status == status)

        return super(TaxRateView, self).get(
            args, query_args=lst, custom_query=custom_query
        )

    @token_required
    @sql_exception_handler
    @finance.arguments(TaxRateCreateSchema)
    @finance.response(400, ResponseSchema)
    @finance.response(201, TaxRateCreateSchema)
    def post(c, self, new_data):
        """Add a new tax_rate"""
        payment_types_ids = new_data.pop("payment_types_ids")
        payment_types = PaymentType.query.filter(
            PaymentType.id.in_(payment_types_ids)
        ).all()
        new_data["payment_types"] = payment_types
        tax_rate = TaxRate(**new_data)
        session.add(tax_rate)
        tax_rate.create_counterparty()
        session.commit()
        new_data["id"] = tax_rate.id
        return new_data


@finance.route("/tax_rate/<int:id>")
class TaxRateIdView(MethodView):
    @token_required
    @finance.response(200, TaxRateRetrieveSchema)
    def get(c, self, id):
        """Get tax_rate by ID"""

        item = TaxRate.get_or_404(id)
        return item

    @token_required
    @sql_exception_handler
    @finance.arguments(TaxRateUpdateSchema)
    @finance.response(200, TaxRateUpdateSchema)
    def put(c, self, update_data, id):
        """Update existing counterparty"""

        item = TaxRate.get_or_404(id)

        payment_types_ids = update_data.pop("payment_types_ids", None)
        payment_types = PaymentType.query.filter(
            PaymentType.id.in_(payment_types_ids)
        ).all()
        update_data["payment_types"] = payment_types

        item.update_counterparty(name=update_data.get("name"))

        # delete all payment types from object
        item.payment_types.clear()

        for col, val in update_data.items():
            setattr(item, col, val)

        session.merge(item)
        session.commit()
        return item

    @token_required
    @sql_exception_handler
    @finance.response(204)
    def delete(c, self, id):
        """Delete tax_rate"""
        TaxRate.delete_with_get(id)
