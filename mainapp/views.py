from django.shortcuts import render,redirect,get_object_or_404
from django.http import HttpResponse,FileResponse,JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.hashers import make_password
from .models import *
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import check_password
from django.utils import timezone
from django.contrib import messages
import re
from django.core.mail import send_mail 
from django.conf import settings
import uuid
from django.db.models import Sum,Count,Q
from django.contrib import messages
from datetime import datetime,timedelta,date
import csv
import os
import pandas as pd
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
import random
from .decorators import role_required
from django.views.decorators.cache import never_cache
from django.db.models.functions import TruncDate
import json

def signup(request):
    if request.method=="POST":
        username=request.POST['username']
        email=request.POST['email']
        raw_password=request.POST['password']
        phone_no=request.POST['phone_no']
        if User.objects.filter(email=email).exists():
            messages.warning(request,"User already exists")
            return redirect("signup")
        if not re.match(r'^[6-9]\d{9}$', phone_no):
            messages.error(request, "Enter valid 10-digit phone number")
            return redirect("signup")
        if User.objects.filter(phone_no=phone_no).exists():
            messages.error(request, "Phone number already registered")
            return redirect("signup")
        try:
            validate_password(raw_password)
        except ValidationError as e:
            messages.error(request,e.messages[0])
            return redirect("signup")
        hash_password=make_password(raw_password)
        User.objects.create(username=username,email=email,password=hash_password,phone_no=phone_no)
        return redirect("login")
    return render(request,"signup.html")

@never_cache
def login(request):
    if request.method=="POST":
        email=request.POST.get("email")
        password=request.POST.get("password")
        remember_me=request.POST.get("remember_me")
        try:
            user=User.objects.get(email=email)
            if check_password(password,user.password):
                request.session["user_id"]=user.id
                request.session["is_logged_in"]=True
                request.session["role"]=user.role.id
                request.session
                if remember_me == "1":
                    request.session.set_expiry(60*60*24*7)
                else:
                    request.session.set_expiry(0)
                if user.role.id==1:
                    return redirect("customer_dashboard")
                elif user.role.id==2:
                    return redirect("agent_dashboard")
                elif user.role.id==3:
                    return redirect("admin_dashboard")
                elif user.role.id==4:
                    return redirect("hub_dashboard")
            else:
                messages.error(request,"Invalid password")
                return redirect("login")
        except User.DoesNotExist:
            messages.error(request,"User does not exist. Please create account")
            return redirect("signup")
    return render(request,"login.html")

def forgot_password(request):
    if request.method == "POST":
        email = request.POST.get("email")

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, "Email not found")
            return redirect("forgot")

        token = str(uuid.uuid4())
        user.reset_token = token
        user.save()

        reset_link = f"http://127.0.0.1:8000/reset/{token}/"

        send_mail(
            "Reset Password",
            f"Click link to reset password:\n{reset_link}",
            settings.DEFAULT_FROM_EMAIL,
            [email]
        )

        messages.success(request, "Reset link sent")
        return redirect("forgot")

    return render(request, "forgot.html")

def reset_password(request, token):
    try:
        user = User.objects.get(reset_token=token)
    except User.DoesNotExist:
        messages.error(request, "Invalid link")
        return redirect("forgot")

    if request.method == "POST":
        p1 = request.POST.get("password")
        p2 = request.POST.get("confirm_password")

        if p1 != p2:
            messages.error(request, "Passwords not match")
            return redirect(request.path)

        user.password = make_password(p1)
        user.reset_token = None
        user.save()

        messages.success(request, "Password changed successfully")
        return redirect("login")

    return render(request, "reset.html")

def home(request):
    return render(request,"home.html")

def about(request):
    return render(request,"about.html")

def contact(request):
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        phone_no=request.POST.get("phone_no")
        subject = request.POST.get("subject")
        message = request.POST.get("message")

        Contact.objects.create(
            name=name,
            email=email,
            phone_no=phone_no,
            subject=subject,
            message=message
        )

        return render(request, "contact.html", {"msg": "Message Sent"})

    return render(request, "contact.html")

def services(request):
    return render(request,"services.html")

@never_cache
@role_required([1])
def customer_dashboard(request):
    if not request.session.get("is_logged_in"):
        return redirect("login")
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("login")
    user = User.objects.get(id=user_id)
    pickups = Pickup.objects.filter(customer=user)
    total_requests = pickups.count()
    completed_requests = pickups.filter(status="Completed").count()
    pending_requests = pickups.filter(status="Pending").count()
    total_earned = Payment.objects.filter(
        user_id=user_id,
        status="Paid"
    ).aggregate(total=Sum("amount"))["total"] or 0
    latest_pickup = Pickup.objects.filter(
        customer_id=user_id
    ).order_by("-id").first()
    payment = None
    if latest_pickup:
        payment = Payment.objects.filter(
            pickup=latest_pickup,
            status="Paid"
        ).first()
    if latest_pickup and latest_pickup.status == "Completed":
        if latest_pickup.actual_time:
            if timezone.now() > latest_pickup.actual_time + timedelta(minutes=1):
                latest_pickup = None
    recent_pickups = Pickup.objects.filter(
        customer_id=user_id
    ).order_by("-id")[:5]
    for p in recent_pickups:
        p.total_amount = PickupTransaction.objects.filter(
            pickup=p
        ).aggregate(total=Sum("total_amount"))["total"] or 0
    context = {
        "user": user,
        "total_requests": total_requests,
        "completed_requests": completed_requests,
        "pending_requests": pending_requests,
        "total_earned": total_earned,
        "recent_pickups": recent_pickups,
        "latest_pickup": latest_pickup,
        "payment": payment, 
    }
    return render(request, "customer_dashboard.html", context)

@role_required([1])
def request_pickup(request):
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("login")
    user = User.objects.get(id=user_id)
    wastes = Ewaste.objects.all()
    zones = Zone.objects.filter(city="Ahmedabad")
    areas = Area.objects.all()
    if request.method == "POST":
        zone_id = request.POST.get("zone")
        area_id = request.POST.get("area")
        zone = Zone.objects.get(id=zone_id)
        area = Area.objects.get(id=area_id)
        quantity = request.POST.get("quantity")
        pickup_date = request.POST.get("pickup_date")
        if pickup_date:
            selected_date = datetime.strptime(pickup_date, "%Y-%m-%d").date()
            if selected_date < date.today():
                messages.error(request, "Past date not allowed")
                return redirect("request_pickup")
        address = request.POST.get("address")
        proposed_datetime = None
        if pickup_date:
            proposed_datetime = datetime.strptime(pickup_date, "%Y-%m-%d")
        agents = User.objects.filter(role__role_name="Agent")
        free_agents = []
        for a in agents:
            busy = Pickup.objects.filter(
                agent=a,
                status="Assigned"
            ).exists()
            if not busy:
                free_agents.append(a)
        if free_agents:
            agent = random.choice(free_agents)
            status_value = "Assigned"
        else:
            agent = None
            status_value = "Pending"
            messages.info(request, "All agents are busy. Your request is in waiting queue.")
        pickup = Pickup.objects.create(
            customer=user,
            pickup_address=address,
            proposed_time=proposed_datetime,
            agent=agent,
            area=area,
            zone=zone,
            status=status_value
        )
        waste_ids = request.POST.get("waste_type")
        if waste_ids:
            waste_ids = waste_ids.split(",")
        else:
            waste_ids = []
        qty = int(quantity) if quantity else 1
        for wid in waste_ids:
            waste = Ewaste.objects.get(id=int(wid))
            PickupTransaction.objects.create(
                pickup=pickup,
                waste=waste,
                waste_quantity=qty,
                total_amount=0,
                status="Collected"
            )
        messages.success(request, "Pickup Request Submitted")
        return redirect("customer_dashboard")
    return render(request, "request_pickup.html", {
        "wastes": wastes,
        "today": date.today(),
        "zone": zones,
        "area": areas
    })

@role_required([1])
def my_request(request):
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("login")
    pickups = Pickup.objects.filter(
        customer_id=user_id
    ).order_by("-request_time")
    context = {
        "pickups": pickups
    }
    return render(request, "my_request.html", context)

@role_required([1])
def customer_payment(request):
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("login")

    payments = Payment.objects.filter(
        user_id=user_id,
    ).order_by("-id")

    return render(request,"customer_payment.html",{
        "payments": payments,
    })

@role_required([1])
def feedback(request):
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("login")
    if request.method == "POST":
        rating = request.POST.get("rating")
        message = request.POST.get("message")
        if not rating:
            messages.error(request, "Please select rating")
            return redirect("feedback")
        if not message:
            messages.error(request, "Please write feedback message")
            return redirect("feedback")
        Feedback.objects.create(
            user_id=user_id,
            rating=int(rating),
            message=message
        )
        messages.success(request, "Feedback Submitted Successfully")
        return redirect("customer_dashboard")
    return render(request, "feedback.html")

@role_required([1])
def profile(request):
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("login")
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        messages.error(request, "User not found")
        return redirect("login")
    name_parts = user.username.split()
    if len(name_parts) >= 2:
        initials = name_parts[0][0].upper() + name_parts[1][0].upper()
    else:
        initials = user.username[0].upper()
    if request.method == "POST":
        username = request.POST.get("username")
        email=request.POST.get("email")
        phone = request.POST.get("phone")
        address = request.POST.get("address")
        if not username or not phone:
            messages.error(request, "Username and Phone required")
            return redirect("profile")
        user.username = username
        user.email=email
        user.phone_no = phone
        user.address = address
        user.save()
        messages.success(request, "Profile Updated Successfully")
        return redirect("profile")
    context = {
        "user": user,
        "initials": initials
    }
    return render(request, "profile.html", context)

@never_cache
def logout_view(request):
    request.session.flush()
    messages.success(request, "Logged out successfully")
    return redirect("login")

@role_required([3])
def admin_dashboard(request):
    if not request.session.get("user_id"):
        return redirect("login")
    user = User.objects.get(id=request.session.get("user_id"))
    total_users = User.objects.count()
    total_requests = Pickup.objects.count()
    pending_requests = Pickup.objects.filter(status="Pending").count()
    completed_requests = Pickup.objects.filter(status="Completed").count()
    total_payment = PickupTransaction.objects.aggregate(
        total=Sum("total_amount")
    )["total"] or 0
    recent_pickups = Pickup.objects.all().order_by("-id")[:5]
    daily_data = Pickup.objects.annotate(
        day=TruncDate("request_time")
    ).values("day").annotate(total=Count("id")).order_by("day")
    months = json.dumps([d["day"].strftime("%d %b") for d in daily_data])
    counts = json.dumps([d["total"] for d in daily_data])
    status_data = Pickup.objects.values("status").annotate(total=Count("id"))
    status_labels = json.dumps([s["status"] for s in status_data])
    status_counts = json.dumps([s["total"] for s in status_data])
    return render(request, "admin_dashboard.html", {
        "user": user,
        "total_users": total_users,
        "total_requests": total_requests,
        "pending_requests": pending_requests,
        "completed_requests": completed_requests,
        "total_payment": total_payment,
        "recent_pickups": recent_pickups,
        "months": months,
        "counts": counts,
        "status_labels": status_labels,
        "status_counts": status_counts,
    })

@role_required([3])
def admin_profile(request):
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("login")
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        messages.error(request, "User not found")
        return redirect("login")
    name_parts = user.username.split()
    if len(name_parts) >= 2:
        initials = name_parts[0][0].upper() + name_parts[1][0].upper()
    else:
        initials = user.username[0].upper()
    if request.method == "POST":
        username = request.POST.get("username")
        email=request.POST.get("email")
        phone = request.POST.get("phone")
        address = request.POST.get("address")
        if not username or not phone:
            messages.error(request, "Username and Phone required")
            return redirect("admin_profile")
        user.username = username
        user.email=email
        user.phone_no = phone
        user.address = address
        user.save()
        messages.success(request, "Profile Updated Successfully")
        return redirect("admin_profile")
    context = {
        "user": user,
        "initials": initials
    }
    return render(request, "admin_profile.html", context)

@role_required([3])
def admin_user(request):
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("login")
    admin = User.objects.get(id=user_id)
    users = User.objects.exclude(role__role_name="Admin")
    return render(request, "admin_user.html", {
        "users": users,
        "admin": admin
    })

@role_required([3])
def delete_user(request, id):
    user = User.objects.filter(id=id).first()
    if user:
        name = user.username
        user.delete()
        messages.success(request, f"{name} deleted successfully")
    return redirect("admin_user")

@role_required([3])
def admin_pickups(request):
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("login")
    pickups = Pickup.objects.all().order_by("-id")
    return render(request, "admin_pickups.html", {
        "pickups": pickups
    })

@role_required([3])
def admin_reports(request):
    if not request.session.get("user_id"):
        return redirect("login")
    admin_id = request.session.get("user_id")
    if request.method == "POST":
        report_type = request.POST.get("report_type")
        file_format = request.POST.get("format")
        folder = os.path.join(settings.MEDIA_ROOT, "reports")
        os.makedirs(folder, exist_ok=True)
        filename = f"{report_type}_{int(datetime.now().timestamp())}"
        if report_type == "Pickup":
            data = Pickup.objects.all().values("id","customer__username","status","request_time")
        elif report_type == "Payment":
            data = PickupTransaction.objects.all().values("id","total_amount")
        else:
            data = User.objects.all().values("id","username","email")
        df = pd.DataFrame(data)
        if df.empty:
            messages.error(request,"No data available")
            return redirect("admin_reports")
        if file_format == "csv":
            filepath = os.path.join(folder,f"{filename}.csv")
            df.to_csv(filepath,index=False)
        elif file_format == "excel":
            filepath = os.path.join(folder,f"{filename}.xlsx")
            df.to_excel(filepath,index=False)
        else:  
            filepath = os.path.join(folder,f"{filename}.pdf")
            doc = SimpleDocTemplate(filepath)
            styles = getSampleStyleSheet()
            title = Paragraph(f"<b>{report_type} REPORT</b>", styles['Title'])
            date_text = Paragraph(
                f"Generated on: {datetime.now().strftime('%d-%m-%Y %H:%M')}",
                styles['Normal']
            )
            data_table = [df.columns.tolist()] + df.values.tolist()
            table = Table(data_table)
            table.setStyle(TableStyle([
                ('BACKGROUND',(0,0),(-1,0),colors.grey),
                ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),
                ('GRID',(0,0),(-1,-1),1,colors.black),
                ('BACKGROUND',(0,1),(-1,-1),colors.beige),
            ]))
            elements = [title, Spacer(1,12), date_text, Spacer(1,20), table]
            doc.build(elements)
        Report.objects.create(
            report_type=report_type,
            file_path=filepath,
            format=file_format,
            admin_id=admin_id,
            generated_datetime=timezone.now()
        )
        messages.success(request,"Report Generated")
        return redirect("admin_reports")
    total_requests = Pickup.objects.count()
    completed_requests = Pickup.objects.filter(status="Completed").count()
    pending_requests = Pickup.objects.filter(status="Pending").count()
    total_payment = PickupTransaction.objects.aggregate(
        total=Sum("total_amount")
    )["total"] or 0
    reports = Report.objects.all().order_by("-generated_datetime")
    pickups = Pickup.objects.all().order_by("-request_time")
    return render(request,"admin_reports.html",{
        "total_requests": total_requests,
        "completed_requests": completed_requests,
        "pending_requests": pending_requests,
        "total_payment": total_payment,
        "reports": reports,
        "pickups": pickups
    })

@role_required([3])
def download_report(request,id):
    report = get_object_or_404(Report,id=id)
    return FileResponse(
        open(report.file_path,"rb"),
        as_attachment=True
    )
@role_required([3])
def add_user(request):
    if not request.session.get("user_id"):
        return redirect("login")
    roles = Role.objects.filter(role_name__in=["Agent","Recyclinghub","Admin"])
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        phone = request.POST.get("phone")
        address = request.POST.get("address")
        role_id = request.POST.get("role")
        zone_id = request.POST.get("zone")
        area_id = request.POST.get("area")
        if User.objects.filter(email=email).exists():
            messages.error(request,"User already exists")
            return redirect("add_user")
        role = Role.objects.get(id=role_id)
        user = User.objects.create(
            username=username,
            email=email,
            password=make_password(password),
            phone_no=phone,
            address=address,
            role=role
        )
        if role.role_name == "Agent" and zone_id:
            zone = Zone.objects.get(id=zone_id)
            zone.agent = user
            zone.save()
        messages.success(request,"User Added Successfully")
        return redirect("admin_user")
    return render(request,"add_user.html",{
        "roles": roles
    })


@role_required([3])
def edit_user(request,id):
    if not request.session.get("user_id"):
        return redirect("login")
    user = User.objects.get(id=id)
    roles = Role.objects.filter(role_name__in=["Customer","Agent","Recyclinghub"])
    zones = Zone.objects.all()
    try:
        agent_zone = Zone.objects.get(agent=user)
    except:
        agent_zone = None
    if request.method == "POST":
        user.username = request.POST.get("username")
        user.email = request.POST.get("email")
        user.phone_no = request.POST.get("phone")
        user.address = request.POST.get("address")
        role_id = request.POST.get("role")
        zone_id = request.POST.get("zone")
        role = Role.objects.get(id=role_id)
        user.role = role
        password = request.POST.get("password")
        if password:
            user.password = make_password(password)
        user.save()
        Zone.objects.filter(agent=user).update(agent=None)

        if role.role_name == "Agent" and zone_id:
            zone = Zone.objects.get(id=zone_id)
            zone.agent = user
            zone.save()
        messages.success(request,"User Updated Successfully")
        return redirect("admin_user")
    return render(request,"edit_user.html",{
        "user": user,
        "roles": roles,
        "zones": zones,
        "agent_zone": agent_zone
    })

@role_required([3])
def admin_payments(request):
    payments = Payment.objects.filter(status="Pending")
    payments_history = Payment.objects.all()
    transactions = PaymentTransaction.objects.select_related(
        'payment', 'payment__user', 'payment__pickup'
    ).all().order_by('-created_at')
    return render(request,"admin_payments.html",{
        "payments": payments,
        "payments_history": payments_history,
        "transactions": transactions, 
    })

@role_required([3])
def make_payment(request, id):
    payment = Payment.objects.get(id=id)
    return render(request, "mock_payment.html", {
        "payment": payment
    })

@role_required([3])
def send_otp(request, payment_id):
    admin = User.objects.filter(role__role_name="Admin").first()
    payment = Payment.objects.get(id=payment_id)
    otp = str(random.randint(1000,9999))
    request.session['otp'] = otp
    send_mail(
        'Your Payment OTP',
        f'Your OTP is {otp}',
        'pvrushti71@gmail.com',
        [admin.email],
        fail_silently=False,
    )
    return JsonResponse({'status': 'OTP sent'})

@role_required([3])
def payment_success(request, id):
    payment = Payment.objects.get(id=id)
    if payment.status == "Paid":
        messages.info(request, "Payment already completed")
        return redirect("admin_payments")
    if request.method == "POST":
        otp = request.POST.get("otp")
        session_otp = request.session.get('otp')
        if otp == session_otp:
            payment.status = "Paid"
            payment.save()
            txn_id = "MOCK" + str(random.randint(10000,99999))
            PaymentTransaction.objects.create(
                payment=payment,
                transaction_id=txn_id,
                gateway="Mock",
                status="Success"
            )
            payment.pickup.status = "Completed"
            payment.pickup.save()
            if 'otp' in request.session:
                del request.session['otp']
            messages.success(request, "Payment Successful")
            return render(request,"payment_success.html",{
                "txn_id": txn_id
            })
        else:
            messages.error(request, "Invalid OTP")
    return render(request,"mock_payment.html",{
        "payment": payment
    })

@role_required([3])
def admin_salary(request):
    current_month = timezone.now().strftime("%B %Y")
    agents = User.objects.filter(role__role_name="Agent")
    paid_agent_ids = Salary.objects.filter(
        month=current_month,
        status="Paid"
    ).values_list('agent_id', flat=True)
    salaries = Salary.objects.select_related('agent').all()
    return render(request, "admin_salary.html", {
        "agents": agents,
        "paid_agent_ids": list(paid_agent_ids),
        "salaries": salaries,
        "current_month": current_month,
    })

@role_required([3])
def pay_salary(request, id):
    agent = get_object_or_404(User, id=id)
    current_month = timezone.now().strftime("%B %Y")
    already_paid = Salary.objects.filter(
        agent=agent,
        month=current_month,
        status="Paid"
    ).exists()
    if already_paid:
        messages.error(request, f"Salary for {agent.username} ({current_month}) is already paid.")
        return redirect("admin_salary")
    salary, created = Salary.objects.get_or_create(
        agent=agent,
        month=current_month,
        defaults={
            'amount': 7000, 
            'status': 'Pending'
        }
    )
    return render(request, "salary_payment.html", {
        "salary": salary
    })

@role_required([3])
def send_salary_otp(request, salary_id):
    admin = User.objects.filter(role__role_name="Admin").first()
    salary = get_object_or_404(Salary, id=salary_id)
    otp = str(random.randint(1000, 9999))
    request.session['salary_otp'] = otp
    send_mail(
        'Salary Payment OTP',
        f'Your OTP for salary payment to {salary.agent.username} ({salary.month}) is: {otp}',
        'pvrushti71@gmail.com',
        [admin.email],
        fail_silently=False,
    )
    return JsonResponse({'status': 'OTP sent'})

@role_required([3])
def salary_payment_success(request, id):
    salary = get_object_or_404(Salary, id=id)
    if salary.status == "Paid":
        messages.info(request, "Salary already paid.")
        return redirect("admin_salary")
    if request.method == "POST":
        otp = request.POST.get("otp")
        session_otp = request.session.get('salary_otp')
        if otp == session_otp:
            salary.status    = "Paid"
            salary.paid_date = timezone.now().date()
            salary.save()
            txn_id = "SAL" + str(random.randint(10000, 99999))
            SalaryTransaction.objects.create(
                salary=salary,
                transaction_id=txn_id,
                gateway="Mock",
                status="Success"
            )
            if 'salary_otp' in request.session:
                del request.session['salary_otp']
            messages.success(request, f"Salary paid successfully to {salary.agent.username}!")
            return render(request, "salary_payment_success.html", {
                "txn_id": txn_id,
                "salary": salary
            })
        else:
            messages.error(request, "Invalid OTP. Please try again.")
    return render(request, "salary_payment.html", {
        "salary": salary
    })

@role_required([2])
def agent_salary(request):
    agent_id = request.session.get("user_id")
    salaries = Salary.objects.filter(agent_id=agent_id)
    return render(request,"agent_salary.html",{
        "salaries": salaries
    })

@role_required([2])
def agent_dashboard(request):  
    agent_id = request.session.get("user_id")  
    if not agent_id:  
        return redirect("login")  
    agent = User.objects.get(id=agent_id)  
    pickups = Pickup.objects.filter(agent_id=agent_id)  
    assigned_requests = Pickup.objects.filter(status="Assigned", agent_id=agent_id).count()
    completed_requests = Pickup.objects.filter(status="Completed", agent_id=agent_id).count()
    transactions = PickupTransaction.objects.filter(  
        pickup__agent_id=agent_id  
    )  
    total_pickups = pickups.count()  
    completed = pickups.filter(status="Completed").count()  
    total_amount = transactions.aggregate(  
        total=Sum("total_amount")  
    )["total"] or 0  
    latest_pickup = Pickup.objects.filter(  
        agent_id=agent_id,  
        status__in=["Assigned", "Started", "Verified"]  
    ).last()  
    pickups = Pickup.objects.filter(agent_id=agent_id).order_by("-id")  
    recent_pickups = pickups[:5]  
    return render(request,"agent_dashboard.html",{  
        "agent": agent,  
        "total_pickups": total_pickups,  
        "completed": completed,  
        "total_amount": total_amount,  
        "recent_pickups": recent_pickups,  
        "completed_requests": completed_requests,  
        "assigned_requests":assigned_requests,  
        "latest_pickup": latest_pickup,  
        "pickups": pickups,  
    })

@role_required([2])
def start_pickup(request,id):
    pickup = Pickup.objects.get(id=id)
    pickup.status = "Started"
    pickup.save()
    return redirect("assigned_pickups")

@role_required([2])
def complete_pickup(request,id):
    pickup = Pickup.objects.get(id=id)
    pickup.status = "Completed"
    pickup.actual_time = timezone.now()
    pickup.save()
    agents = User.objects.filter(role__role_name="Agent")
    for a in agents:
        busy = Pickup.objects.filter(agent=a, status="Assigned").exists()
        if not busy:
            pending = Pickup.objects.filter(status="Pending").order_by("id").first()
            if pending:
                pending.agent = a
                pending.status = "Assigned"
                pending.save()
    return redirect("assigned_pickups")

@role_required([2])
def assigned_pickups(request):
    agent_id = request.session.get("user_id")
    if not agent_id:
        return redirect("login")
    agent = User.objects.get(id=agent_id)
    pickup_address=Pickup.objects.filter(agent_id=agent_id)
    pickups = Pickup.objects.filter(agent_id=agent_id)
    assigned_requests = Pickup.objects.filter(status="Assigned").count()
    pending_requests = Pickup.objects.filter(status="Pending").count()
    completed_requests = Pickup.objects.filter(status="Completed").count()
    recent_pickups = pickups.order_by("-id")[:5]
    return render(request,"assigned_pickups.html",{
        "agent": agent,
        "pickup_address":pickup_address,
        "recent_pickups": recent_pickups,
        "pending_requests": pending_requests,
        "completed_requests": completed_requests,
        "assigned_requests":assigned_requests,
    })
    
@role_required([2])
def verify_pickup(request, id):
    agent_id = request.session.get("user_id")
    if not agent_id:
        return redirect("login")
    pickup = Pickup.objects.get(id=id)
    transactions = PickupTransaction.objects.filter(
        pickup=pickup,
        status="Collected"
    )
    hub = User.objects.filter(role__role_name="Recyclinghub").first()
    if request.method == "POST":
        for t in transactions:
            qty = request.POST.get(f"qty_{t.id}")
            if qty is not None:
                qty = int(qty)
                amount = t.waste.price * qty  
                t.waste_quantity = qty
                t.total_amount = amount       
                t.status = "Verified"
                if hub:
                    t.recycling_hub = hub
                t.save()
        total = PickupTransaction.objects.filter(
            pickup=pickup
        ).aggregate(total=Sum("total_amount"))["total"] or 0
        Payment.objects.create(
            user=pickup.customer,
            pickup=pickup,
            amount=total,
            payment_method="Mock",
            status="Pending"
        )
        pickup.status = "Verified"
        pickup.save()
        messages.success(request, "Pickup Verified Successfully")
        return redirect("assigned_pickups")
    return render(request, "verify_pickup.html", {
        "pickup": pickup,
        "transactions": transactions
    })


@role_required([2])
def pickup_history(request):
    agent_id = request.session.get("user_id")
    if not agent_id:
        return redirect("login")
    pickups = Pickup.objects.filter(
        agent_id=agent_id
    ).order_by("-id")
    return render(request,"pickup_history.html",{
        "pickups": pickups
    })

@role_required([2])
def agent_profile(request):
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("login")
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        messages.error(request, "User not found")
        return redirect("login")
    name_parts = user.username.split()
    if len(name_parts) >= 2:
        initials = name_parts[0][0].upper() + name_parts[1][0].upper()
    else:
        initials = user.username[0].upper()
    if request.method == "POST":
        username = request.POST.get("username")
        email=request.POST.get("email")
        phone = request.POST.get("phone")
        address = request.POST.get("address")
        if not username or not phone:
            messages.error(request, "Username and Phone required")
            return redirect("agent_profile")
        user.username = username
        user.email=email
        user.phone_no = phone
        user.address = address
        user.save()
        messages.success(request, "Profile Updated Successfully")
        return redirect("agent_profile")
    context = {
        "user": user,
        "initials": initials
    }
    return render(request, "agent_profile.html", context)

@role_required([4])
def hub_dashboard(request):
    hub_id = request.session.get("user_id")
    if not hub_id:
        return redirect("login")
    transactions = PickupTransaction.objects.filter(
        recycling_hub_id=hub_id
    )
    total_received = transactions.count()
    verified = transactions.filter(status="Verified").count()
    total_quantity = transactions.aggregate(
        total=Sum("waste_quantity")
    )["total"] or 0
    recent_transactions = transactions.order_by("-id")[:8]
    return render(request,"hub_dashboard.html",{
        "total_received": total_received,
        "verified": verified,
        "total_quantity": total_quantity,
        "transactions": recent_transactions
    })

@role_required([4])
def hub_profile(request):
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("login")
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        messages.error(request, "User not found")
        return redirect("login")
    name_parts = user.username.split()
    if len(name_parts) >= 2:
        initials = name_parts[0][0].upper() + name_parts[1][0].upper()
    else:
        initials = user.username[0].upper()
    if request.method == "POST":
        username = request.POST.get("username")
        phone = request.POST.get("phone")
        email=request.POST.get("email")
        address = request.POST.get("address")
        if not username or not phone:
            messages.error(request, "Username and Phone required")
            return redirect("hub_profile")
        user.username = username
        user.email=email
        user.phone_no = phone
        user.address = address
        user.save()
        messages.success(request, "Profile Updated Successfully")
        return redirect("hub_profile")
    context = {
        "user": user,
        "initials": initials
    }
    return render(request, "hub_profile.html", context)

@role_required([4])
def received_waste(request):
    hub_id = request.session.get("user_id")
    if not hub_id:
        return redirect("login")
    transactions = PickupTransaction.objects.filter(
        recycling_hub_id=hub_id
    ).values(
        "waste__waste_type"
    ).annotate(
        total_qty=Sum("waste_quantity")   
    ).order_by("-total_qty")
    return render(request,"received_waste.html",{
        "transactions": transactions
    })

@role_required([4])
def verify_waste(request,id):
    hub_id = request.session.get("user_id")
    if not hub_id:
        return redirect("login")
    t = PickupTransaction.objects.get(id=id)
    t.status = "Verified"
    t.save()
    messages.success(request,"Waste Verified")
    return redirect("received_waste")

@role_required([4])
def reject_waste(request,id):
    hub_id = request.session.get("user_id")
    if not hub_id:
        return redirect("login")
    t = PickupTransaction.objects.get(id=id)
    t.status = "Rejected"
    t.save()
    messages.warning(request,"Waste Rejected")
    return redirect("received_waste")

@role_required([4])
def hub_verify_waste(request, id):
    hub_id = request.session.get("user_id")
    if not hub_id:
        return redirect("login")
    t = PickupTransaction.objects.get(id=id)
    t.status = "Verified"
    t.recycling_hub_id = hub_id
    t.save()
    messages.success(request,"Waste Verified")
    return redirect("received_waste")

@role_required([4])
def hub_complete_waste(request, id):
    hub_id = request.session.get("user_id")
    if not hub_id:
        return redirect("login")
    t = PickupTransaction.objects.get(id=id)
    t.status = "Completed"
    t.save()
    messages.success(request,"Waste Processing Completed")
    return redirect("received_waste")

@role_required([4])
def hub_report(request):
    hub_id = request.session.get("user_id")
    if not hub_id:
        return redirect("login")
    if request.method == "POST":
        report_type = request.POST.get("report_type")
        file_format = request.POST.get("format")
        folder = os.path.join(settings.MEDIA_ROOT, "hub_report")
        os.makedirs(folder, exist_ok=True)
        filename = f"{report_type}_{int(datetime.now().timestamp())}"
        if report_type == "Completed":
            data = PickupTransaction.objects.filter(
                recycling_hub_id=hub_id,
                status="Completed"
            ).values("id","waste__waste_type","waste_quantity","total_amount")
        else:  # Settlement Report
            data = Settlement.objects.filter(
                recycling_hub_id=hub_id
            ).values("id","amount","status","settlement_date")
        df = pd.DataFrame(data)
        if df.empty:
            messages.error(request,"No data available")
            return redirect("hub_report")
        if file_format == "csv":
            filepath = os.path.join(folder,f"{filename}.csv")
            df.to_csv(filepath,index=False)
        else:
            filepath = os.path.join(folder,f"{filename}.pdf")
            doc = SimpleDocTemplate(filepath)
            styles = getSampleStyleSheet()
            title = Paragraph(
                f"<b>{report_type} REPORT</b>",
                styles['Title']
            )
            date_text = Paragraph(
                f"Generated on: {datetime.now().strftime('%d-%m-%Y %H:%M')}",
                styles['Normal']
            )
            data_table = [df.columns.tolist()] + df.values.tolist()
            table = Table(data_table)
            table.setStyle(TableStyle([
                ('BACKGROUND',(0,0),(-1,0),colors.grey),
                ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),
                ('GRID',(0,0),(-1,-1),1,colors.black),
                ('BACKGROUND',(0,1),(-1,-1),colors.beige),
            ]))
            elements = [title, Spacer(1,12), date_text, Spacer(1,20), table]
            doc.build(elements)
        Report.objects.create(
            report_type=report_type,
            file_path=filepath,
            format=file_format,
            hub_id=hub_id,
            generated_datetime=timezone.now()
        )
        messages.success(request,"Report Generated")
        return redirect("hub_report")
    reports = Report.objects.all().order_by("-generated_datetime")
    return render(request,"hub_report.html",{
        "reports": reports
    })

@role_required([4])
def hub_send_otp(request):
    hub_id = request.session.get("user_id")
    if not hub_id:
        return JsonResponse({'error': 'Not logged in'}, status=401)
    hub = User.objects.get(id=hub_id)
    otp = str(random.randint(1000,9999))
    request.session['hub_otp'] = otp
    send_mail(
        'Hub Payment OTP',
        f'Your OTP is {otp}',
        'pvrushti71@gmail.com',
        [hub.email],
        fail_silently=False,
    )
    return JsonResponse({'status': 'OTP sent'})

@role_required([4])
def hub_make_payment(request):
    hub_id = request.session.get("user_id")
    if not hub_id:
        return redirect("login")
    hub = User.objects.get(id=hub_id)
    transactions = PickupTransaction.objects.filter(
        recycling_hub_id=hub_id,
        status="Verified"
    )
    total = sum(t.total_amount * 2 for t in transactions)
    for t in transactions:
        t.new_amount=t.total_amount * 2
    return render(request,"hub_payment.html",{
        "transactions": transactions,
        "total": total
    })

@role_required([4])
def hub_payment_verify(request):
    hub_id = request.session.get("user_id")
    if not hub_id:
        return redirect("login")
    transactions = PickupTransaction.objects.filter(
        recycling_hub_id=hub_id,
        status="Verified"
    )
    total = sum(t.total_amount * 2 for t in transactions)
    if request.method == "POST":
        user_otp = request.POST.get("otp")
        session_otp = request.session.get("hub_otp")
        if user_otp == session_otp:
            Settlement.objects.create(
                recycling_hub_id=hub_id,
                amount=total,
                status="Paid",
                payer_name="Recycling Hub"
            )
            transactions.update(status="Settled")
            if 'hub_otp' in request.session:
                del request.session['hub_otp']
            messages.success(request, "Payment Successful")
            return redirect("hub_dashboard")
        else:
            messages.error(request, "Invalid OTP")
    return render(request,"hub_payment.html",{
        "transactions": transactions,
        "total": total
    })

@role_required([4])
def hub_history(request):
    hub_id = request.session.get("user_id")
    hub = User.objects.get(id=hub_id)
    pending_transactions = PickupTransaction.objects.filter(
        recycling_hub_id=hub_id,
        status="Verified"
    )
    pending_total = sum(t.total_amount * 2 for t in pending_transactions)
    for t in pending_transactions:
        t.new_amount=t.total_amount * 2
    # Card 2 - jo already pay ho gaye
    settlements = Settlement.objects.filter(
        recycling_hub_id=hub_id
    ).order_by('-id')
    return render(request, "hub_history.html", {
        "hub": hub,
        "pending_transactions": pending_transactions,
        "pending_total": pending_total,
        "settlements": settlements,
        
    })

def admin_settlements(request):
    admin_id = request.session.get("user_id")
    if not admin_id:
        return redirect("login")
    settlements = Settlement.objects.all().order_by("-id")
    total_received = settlements.aggregate(
        total=Sum("amount")
    )["total"] or 0
    return render(request, "admin_settlements.html", {
        "settlements": settlements,
        "total_received": total_received
    })

@csrf_exempt
def update_agent_location(request):

    if request.method == "POST":

        data = json.loads(request.body)

        agent_id = request.session.get("user_id")

        AgentLocation.objects.update_or_create(
            agent_id=agent_id,
            defaults={
                "latitude": data["latitude"],
                "longitude": data["longitude"]
            }
        )

        return JsonResponse({
            "status": "success"
        })


def get_agent_location(request, agent_id):

    try:

        location = AgentLocation.objects.get(
            agent_id=agent_id
        )

        return JsonResponse({
            "latitude": location.latitude,
            "longitude": location.longitude
        })

    except AgentLocation.DoesNotExist:

        return JsonResponse({
            "error": "Location not found"
        })