from django import forms
from .models import Transaction
from accounts.models import UserBankAccount
from django.contrib.auth.models import User
from transactions.constants import DEPOSIT
from django.db.models import Sum
class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = [
            'amount',
            'transaction_type'
        ]

    def __init__(self, *args, **kwargs):
        self.user_account = kwargs.pop('account') # account value ke pop kore anlam
        super().__init__(*args, **kwargs)
        self.fields['transaction_type'].disabled = True # ei field disable thakbe
        self.fields['transaction_type'].widget = forms.HiddenInput() # user er theke hide kora thakbe

    def save(self, commit=True):
        self.instance.account = self.user_account
        self.instance.balance_after_transaction = self.user_account.balance
        return super().save()
    
class DepositForm(TransactionForm):
    def clean_amount(self):
        min_deposit_amount = 100
        amount = self.cleaned_data.get('amount')
        if amount < min_deposit_amount :
            raise forms.ValidationError(
                f'You need to deposit at least {min_deposit_amount} $'
            )
        
        return amount
    


class WithdrawForm(TransactionForm):

    def clean_amount(self):
        account = self.user_account
        amount = self.cleaned_data.get('amount')
        min_withdraw_amount = 500
        max_withdraw_amount = 200000
        balance = account.balance
        if amount < min_withdraw_amount:
            raise forms.ValidationError(
                f'You can withdraw at least {min_withdraw_amount} $'
            )

        if amount > max_withdraw_amount:
            raise forms.ValidationError(
                f'You can withdraw at most {max_withdraw_amount} $'
            )
        
        if amount > balance:
            total_deposited = Transaction.objects.filter(
                account = account,
                transaction_type = DEPOSIT,
            ).aggregate(total_deposite = Sum('amount'))['total_deposite']

            if total_deposited < amount:
                raise forms.ValidationError(
                    'The bank is bankrupt ,unable to withdraw the requested amount.'

                )
            else:
                raise forms.ValidationError(
                    f'You have {balance} $ in your account. '
                    'You cannot withdraw more than your account balance'
                )
        return amount


class LoanRequestForm(TransactionForm):
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')

        return amount



class TransferForm(forms.Form):
    recipient = forms.ModelChoiceField(queryset=User.objects.all())
    amount = forms.DecimalField(max_digits=12,decimal_places=2)

    def __init__(self,*args,**kwargs):
        self.sender_account = kwargs.pop('account')
        super().__init__(*args,**kwargs)

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if self.sender_account.balance < amount:
            raise forms.ValidationError('Insufficient balance')
        return amount
    
    def clean_recipient(self):
        recipient = self.cleaned_data.get('recipient')
        try:
            recipient_account = recipient.account
        except UserBankAccount.DoesNotExist:
            raise forms.ValidationError('Recipient does not have a bank account')
        return recipient
    
    def save(self,commit=True):
        recipient = self.cleaned_data.get('recipient')
        amount = self.cleaned_data.get('amount')

        sender_account = self.sender_account
        recipient_account = recipient.account

        sender_account.balance  -= amount
        recipient_account.balance  += amount

        sender_account.save(update_fields =['balance'])
        recipient_account.save(update_fields =['balance'])

        return recipient,amount


