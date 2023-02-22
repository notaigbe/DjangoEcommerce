import json
import os

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ObjectDoesNotExist
from django.core.serializers import serialize
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.views import generic
from django.views.generic import ListView, DetailView, View
from django.utils import timezone
from pypaystack import Transaction
from rave_python import Rave, rave
from rave_python.rave_exceptions import TransactionVerificationError

from .forms import CheckoutForm, RegistrationForm, AccountUpdateform
from .models import (
    Item,
    Order,
    OrderItem,
    CheckoutAddress,
    Payment, Deal, Stock
)

import stripe

stripe.api_key = settings.STRIPE_KEY


# Create your views here.
class HomeView(ListView):
    model = Item
    template_name = "home.html"


class ProductView(DetailView):
    model = Item
    template_name = "product.html"


class OrderSummaryView(LoginRequiredMixin, View):
    def get(self, *args, **kwargs):

        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            context = {
                'object': order
            }
            return render(self.request, 'order_summary.html', context)
        except ObjectDoesNotExist:
            messages.info(self.request, "You do not have an order")
            return redirect("/")


class OrdersView(LoginRequiredMixin, View):
    def get(self, *args, **kwargs):

        try:
            orders = Order.objects.order_by('-ordered_date')
            context = {
                'orders': orders
            }
            return render(self.request, 'orders.html', context)
        except ObjectDoesNotExist:
            messages.info(self.request, "You do not have an order")
            return redirect("/")


class CheckoutView(View):
    def get(self, *args, **kwargs):
        form = CheckoutForm()
        order = Order.objects.get(user=self.request.user, ordered=False)
        context = {
            'form': form,
            'order': order
        }
        return render(self.request, 'checkout.html', context)

    def post(self, *args, **kwargs):
        form = CheckoutForm(self.request.POST or None)

        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            if form.is_valid():
                street_address = form.cleaned_data.get('street_address')
                apartment_address = form.cleaned_data.get('apartment_address')
                country = form.cleaned_data.get('country')
                phone = form.cleaned_data.get('phone')
                zip = form.cleaned_data.get('zip')
                # TODO: add functionality for these fields
                # same_billing_address = form.cleaned_data.get('same_billing_address')
                # save_info = form.cleaned_data.get('save_info')
                payment_option = form.cleaned_data.get('payment_option')

                checkout_address = CheckoutAddress(
                    user=self.request.user,
                    street_address=street_address,
                    apartment_address=apartment_address,
                    country=country,
                    phone=phone,
                    zip=zip
                )
                checkout_address.save()
                order.checkout_address = checkout_address
                order.save()

                if payment_option == 'S':
                    return redirect('core:payment', payment_option='stripe')
                elif payment_option == 'P':
                    return redirect('core:payment', payment_option='paypal')
                elif payment_option == 'F':
                    return redirect('core:payment', payment_option='flutterwave')
                else:
                    messages.warning(self.request, "Invalid Payment option")
                    return redirect('core:checkout')

        except ObjectDoesNotExist:
            messages.error(self.request, "You do not have an order")
            return redirect("core:order-summary")


class PaymentView(View):
    def get(self, *args, **kwargs):
        order = Order.objects.get(user=self.request.user, ordered=False)
        context = {
            'order': order
        }
        return render(self.request, "payment.html", context)

    def post(self, *args, **kwargs):
        order = Order.objects.get(user=self.request.user, ordered=False)
        token = self.request.POST.get('stripeToken')
        amount = int(order.get_total_price() * 100)  # cents

        try:
            charge = stripe.Charge.create(
                amount=amount,
                currency="usd",
                source=token
            )

            # create payment
            payment = Payment()
            payment.stripe_id = charge['id']
            payment.user = self.request.user
            payment.amount = order.get_total_price()
            payment.save()

            # assign payment to order
            order.ordered = True
            order.payment = payment
            order.save()

            messages.success(self.request, "Success make an order")
            return redirect('/')

        except stripe.error.CardError as e:
            body = e.json_body
            err = body.get('error', {})
            messages.error(self.request, f"{err.get('message')}")
            return redirect('/')

        except stripe.error.RateLimitError as e:
            # Too many requests made to the API too quickly
            messages.error(self.request, "To many request error")
            return redirect('/')

        except stripe.error.InvalidRequestError as e:
            # Invalid parameters were supplied to Stripe's API
            messages.error(self.request, "Invalid Parameter")
            return redirect('/')

        except stripe.error.AuthenticationError as e:
            # Authentication with Stripe's API failed
            # (maybe you changed API keys recently)
            messages.error(self.request, "Authentication with stripe failed")
            return redirect('/')

        except stripe.error.APIConnectionError as e:
            # Network communication with Stripe failed
            messages.error(self.request, "Network Error")
            return redirect('/')

        except stripe.error.StripeError as e:
            # Display a very generic error to the user, and maybe send
            # yourself an email
            messages.error(self.request, "Something went wrong")
            return redirect('/')

        except Exception as e:
            # Something else happened, completely unrelated to Stripe
            messages.error(self.request, "Not identified error")
            return redirect('/')


@login_required
def complete_payment(request):
    token = ''
    status = False
    reference = ''
    amount = 0
    flw_ref = ''

    try:
        if request.GET.get('reference'):
            reference = request.GET.get('reference')
            transaction = Transaction(os.environ.get('PAYSTACK_SECRET_KEY'))
            response = transaction.verify(reference)
            print(response[3]['id'])
            token = response[3]['id']
            status = response[2]
            reference = response[3]['reference']
            amount = response[3]['amount']/100

        else:
            rave_key = Rave(os.environ.get('RAVE_PUBLIC_KEY'), os.environ.get('RAVE_SECRET_KEY'))
            tx_ref = request.GET.get('tx_ref')
            response = rave_key.Card.verify(tx_ref)
            print(response)
            token = response["flwRef"]
            if not response['error']:
                status = 'Verified'
            else:
                status = 'Verification Error'
            reference = response['txRef']
            amount = response['amount']

        order = Order.objects.get(user=request.user, ordered=False)

        # create payment
        payment = Payment()
        payment.transaction_id = token
        payment.tx_ref = reference
        payment.pay_status = status
        payment.user = request.user
        payment.amount = amount
        payment.save()

        # assign payment to order
        order.ordered = True
        order.payment = payment
        order.save()

        messages.success(request, "Your order was successful")
        return redirect('/')

    except TransactionVerificationError as e:
        messages.error(request, e.err["errMsg"])
        return redirect('/')
    except Exception as e:
        # Something else happened, completely unrelated to Stripe
        messages.error(request, str(e))
        return redirect('/')


@login_required
def add_to_cart(request, pk):
    item = get_object_or_404(Item, pk=pk)
    if item.current_stock > 0:
        order_item, created = OrderItem.objects.get_or_create(
            item=item,
            user=request.user,
            ordered=False
        )
        order_qs = Order.objects.filter(user=request.user, ordered=False)

        if order_qs.exists():
            order = order_qs[0]

            if order.items.filter(item__pk=item.pk).exists():
                order_item.quantity += 1
                order_item.save()
                item.current_stock -= 1
                item.save()
                messages.info(request, "Added quantity Item")
                return redirect("core:order-summary")
            else:
                order.items.add(order_item)
                item.current_stock -= order_item.quantity
                item.save()
                messages.info(request, "Item added to your cart")
                return redirect("core:order-summary")
        else:
            ordered_date = timezone.now()
            order = Order.objects.create(user=request.user, ordered_date=ordered_date)
            order.items.add(order_item)
            messages.info(request, "Item added to your cart")
            return redirect("core:order-summary")
    else:
        messages.info(request, "Item out of stock")
        return redirect("core:product", pk=pk)


@login_required
def remove_from_cart(request, pk):
    item = get_object_or_404(Item, pk=pk)
    order_qs = Order.objects.filter(
        user=request.user,
        ordered=False
    )
    if order_qs.exists():
        order = order_qs[0]
        if order.items.filter(item__pk=item.pk).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                user=request.user,
                ordered=False
            )[0]
            order_item.delete()
            item.current_stock += order_item.quantity
            item.save()
            messages.info(request, "Item \"" + order_item.item.item_name + "\" remove from your cart")
            return redirect("core:order-summary")
        else:
            messages.info(request, "This Item not in your cart")
            return redirect("core:product", pk=pk)
    else:
        # add message doesn't have order
        messages.info(request, "You do not have an Order")
        return redirect("core:product", pk=pk)


@login_required
def reduce_quantity_item(request, pk):
    item = get_object_or_404(Item, pk=pk)
    order_qs = Order.objects.filter(
        user=request.user,
        ordered=False
    )
    if order_qs.exists():
        order = order_qs[0]
        if order.items.filter(item__pk=item.pk).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                user=request.user,
                ordered=False
            )[0]
            if order_item.quantity > 1:
                order_item.quantity -= 1
                order_item.save()
                item.current_stock += 1
                item.save()
            else:
                order_item.delete()
                item.current_stock += order_item.quantity
                item.save()
            messages.info(request, "Item quantity was updated")
            return redirect("core:order-summary")
        else:
            messages.info(request, "This Item not in your cart")
            return redirect("core:order-summary")
    else:
        # add message doesn't have order
        messages.info(request, "You do not have an Order")
        return redirect("core:order-summary")


def index(request):
    products = Order.objects.all()
    deal = Deal.objects.filter(pk=1)
    return render(request, 'index_2.html', {'page': 'index', 'products': products, 'deal': deal})


def verify_payment(request):
    print(request.user)
    status = request.GET.get('status')
    transaction_id = request.GET.get('transaction_id')
    tx_ref = request.GET.get('tx_ref')

    try:
        rave = Rave('RAVE_PUBLIC_KEY', 'RAVE_SECRET_KEY')
        res = rave.Card.verify(tx_ref)

        messages.success(request, f'Payment {status}')

    except TransactionVerificationError as e:
        messages.error(request, f'Payment {status} {e.err["errMsg"]}')
        print(e.err["errMsg"])
        print(e.err["flwRef"])
    return redirect('/')


class SignUpView(generic.CreateView):
    form_class = RegistrationForm
    success_url = reverse_lazy("login")
    template_name = "registration/signup.html"


def account_view(request):
    """
      Renders userprofile page "
    """
    if not request.user.is_authenticated:
        return redirect("login")
    context = {}
    if request.POST:
        form = AccountUpdateform(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "profile Updated")
        else:
            messages.error(request, "Please Correct Below Errors")
    else:
        form = AccountUpdateform(
            initial={
                'email': request.user.email,
                'username': request.user.username,
            }
        )
    context['account_form'] = form

    return render(request, "registration/userprofile.html", context)

def latest_orders(request):
    items = []
    orders = Order.objects.order_by('-ordered_date')[:10] # get the latest 10 orders
    for order in orders:
        for item in order.items.all():
            items.append(str(item))


    data = [{'id': order.id,
            'user':{
                'first_name': order.user.first_name,
                'last_name': order.user.last_name,
            },
            'items': [items.append(str(item) for item in order.items.all()) ],
            'start_date': order.start_date.strftime('%Y-%m-%d %H:%M:%S'),
            'ordered_date': order.ordered_date.strftime('%Y-%m-%d %H:%M:%S') if order.ordered_date else '',
            'ordered': order.ordered,
            'checkout_address': {
                'street': order.checkout_address.street_address,
                'apartment': order.checkout_address.apartment_address,
                'country': str(order.checkout_address.country),
                'zip': order.checkout_address.zip,
                'phone': order.checkout_address.phone,
            } if order.checkout_address else '',
            'payment': {
                'transaction_id': order.payment.transaction_id,
                'tx_ref': order.payment.tx_ref,
                'pay_status': order.payment.pay_status,
                'amount': order.payment.amount,
            } if order.payment else '',
             'delivery_status': order.delivery_status,
        } for order in orders]
    return JsonResponse(data, safe=False)

def update_status(request):
    if request.method == "POST":
        _id = request.POST.get("id")
        status = request.POST.get("status")
        print(status)
        # Update the item
        item = Order.objects.get(pk=_id)
        item.delivery_status = status
        item.save()

        # Render the updated table row
        items = Order.objects.all()
        context = {"items": items}
        html = render_to_string("orders.html", context)
        return JsonResponse({"html": html})
    else:
        return JsonResponse({})