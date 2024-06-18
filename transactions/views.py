from django.shortcuts import render,redirect

# Create your views here.

from django.http import HttpResponse
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView
from transactions.models import Transaction
from transactions.constants import DEPOSIT, WITHDRAWAL,LOAN, LOAN_PAID
from django.views import View
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.core.mail import EmailMessage
from transactions.forms import (
    DepositForm,
    WithdrawForm,
    LoanRequestForm,
    TransferForm,
)
from django.shortcuts import get_object_or_404
from transactions.models import Transaction
from django.db.models import Sum
from datetime import datetime


def send_transfer_email(to_email,user, amount,recipient, subject, template):
    message = render_to_string(template, {
        'user' : user,
        'amount' : amount,
        'recipient': recipient,
    })

    send_email = EmailMultiAlternatives(subject, '', to=[to_email])
    send_email.attach_alternative(message, "text/html")
    send_email.send()



class TransferMoneyView(LoginRequiredMixin,View):
    form_class = TransferForm
    template_name = 'transactions/transfer_form.html'

    def get(self,request):
        form = self.form_class(account = request.user.account)
        return render(request,self.template_name,{'form': form})
    
    def post(self,request):
        form = self.form_class(request.POST,account = request.user.account)
        if form.is_valid():
            recipient,amount = form.save(commit=False)
            messages.success(request, f'Successfully transferred {"{:,.2f}".format(float(amount))}$ to {recipient.username}')

            # sender email
            send_transfer_email(request.user.email,request.user, amount,recipient, "Money transferred", "transactions/sender_email.html")
            
            # recipient email
            send_transfer_email(recipient.email,request.user, amount,recipient, "Money received", "transactions/recipient_email.html")

            return redirect('transfer_money')
        

        return render(request, self.template_name, {'form': form})






class TransactionCreateMixin(LoginRequiredMixin,CreateView):
    template_name = 'transactions/transaction_form.html'
    model = Transaction
    success_url = reverse_lazy('transaction_report')
    title = ''

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({
            'account': self.request.user.account,
        })
        return kwargs
    
    def get_context_data(self,**kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'title': self.title,

        })
        return context
    

class DepositMoneyView(TransactionCreateMixin):
    form_class = DepositForm
    title = 'Deposite Form'

    def get_initial(self):
        initial = {'transaction_type': DEPOSIT}
        return initial
    
    def form_valid(self,form):
        amount = form.cleaned_data.get('amount')
        account = self.request.user.account
        account.balance += amount
        account.save(
            update_fields = [
                'balance',
            ]
        )
        
        messages.success(

            self.request,
            f'{"{:,.2f}".format(float(amount))}$ was deposited to your account successfully'
        )
        return super().form_valid(form)


class WithdrawMoneyView(TransactionCreateMixin):
    form_class = WithdrawForm
    title = 'Withdraw Money'

    def get_initial(self):
        initial = {'transaction_type': WITHDRAWAL}
        return initial

    def form_valid(self, form):
        amount = form.cleaned_data.get('amount')

        self.request.user.account.balance -= form.cleaned_data.get('amount')
        # balance = 300
        # amount = 5000
        self.request.user.account.save(update_fields=['balance'])

        messages.success(
            self.request,
            f'Successfully withdrawn {"{:,.2f}".format(float(amount))}$ from your account'
        )
       
        return super().form_valid(form)



class LoanRequestView(TransactionCreateMixin):
    form_class = LoanRequestForm
    title = 'Request For Loan'

    def get_initial(self):
        initial = {'transaction_type': LOAN}
        return initial

    def form_valid(self, form):
        amount = form.cleaned_data.get('amount')
        current_loan_count = Transaction.objects.filter(
            account=self.request.user.account,transaction_type=3,loan_approve=True).count()
        if current_loan_count >= 3:
            return HttpResponse("You have cross the loan limits")
        messages.success(
            self.request,
            f'Loan request for {"{:,.2f}".format(float(amount))}$ submitted successfully'
        )

        return super().form_valid(form)
    


class TransactionReportView(LoginRequiredMixin, ListView):
    template_name = 'transactions/transaction_report.html'
    model = Transaction
    balance = 0 # filter korar pore ba age amar total balance ke show korbe
    
    def get_queryset(self):
        queryset = super().get_queryset().filter(
            account=self.request.user.account
        )
        start_date_str = self.request.GET.get('start_date')
        end_date_str = self.request.GET.get('end_date')
        
        if start_date_str and end_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            
            queryset = queryset.filter(timestamp__date__gte=start_date, timestamp__date__lte=end_date)
            self.balance = Transaction.objects.filter(
                timestamp__date__gte=start_date, timestamp__date__lte=end_date
            ).aggregate(Sum('amount'))['amount__sum']
        else:
            self.balance = self.request.user.account.balance
       
        return queryset.distinct() # unique queryset hote hobe
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'account': self.request.user.account
        })

        return context
    

class PayLoanView(LoginRequiredMixin, View):
    def get(self, request, loan_id):
        # here loan holo transaction object
        loan = get_object_or_404(Transaction, id=loan_id)
        print(loan)
        if loan.loan_approve:
            user_account = loan.account
                # Reduce the loan amount from the user's balance
                # 5000, 500 + 5000 = 5500
                # balance = 3000, loan = 5000
            if loan.amount < user_account.balance:
                user_account.balance -= loan.amount
                loan.balance_after_transaction = user_account.balance
                user_account.save()
                loan.transaction_type = LOAN_PAID
                loan.save()
                return redirect('loan_list')
            else:
                messages.error(
            self.request,
            f'Loan amount is greater than available balance'
        )

        return redirect('loan_list')


class LoanListView(LoginRequiredMixin,ListView):
    model = Transaction
    template_name = 'transactions/loan_request.html'
    context_object_name = 'loans' # loan list ta ei loans context er moddhe thakbe
    
    def get_queryset(self):
        user_account = self.request.user.account
        queryset = Transaction.objects.filter(account=user_account,transaction_type=3)
        return queryset
    


