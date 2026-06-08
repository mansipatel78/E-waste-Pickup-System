from django.db import models
# from django.utils.timezone import timedelta

# Role Table
class Role(models.Model):
    role_name = models.CharField(max_length=20)

    def __str__(self):
        return self.role_name


class User(models.Model):
    username = models.CharField(max_length=50)
    email = models.EmailField(unique=True)
    phone_no = models.CharField(max_length=10, unique=True)
    password = models.CharField(max_length=50)
    address = models.TextField(null=True,blank=True)
    role = models.ForeignKey(Role, on_delete=models.CASCADE ,default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    reset_token=models.CharField(max_length=100,null=True,blank=True)

    def __str__(self):
        return self.username

class Contact(models.Model):
    name = models.CharField(max_length=50)
    email = models.EmailField()
    phone_no = models.CharField(max_length=10,unique=True,null=True)
    subject = models.CharField(max_length=50)
    message = models.TextField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    
class Zone(models.Model):
    zone_name = models.CharField(max_length=100)
    agent = models.ForeignKey(User, on_delete=models.CASCADE)
    state = models.CharField(max_length=50)
    city = models.CharField(max_length=50)
    def __str__(self):
        return self.zone_name

class Area(models.Model):
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE)
    area_name = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    def __str__(self):
        return self.area_name
    
    
class Pickup(models.Model):
    STATUS_CHOICES = [
        ("Pending","Pending"),
        ("Assigned","Assigned"),
        ("Started","Started"),
        ("Verified","Verified"),
        ("Completed","Completed"),
    ]
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="customer_pickups")
    agent = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="agent_pickups")
    pickup_address = models.CharField(max_length=200)
    zone = models.ForeignKey(Zone, on_delete=models.SET_NULL, null=True)
    area = models.ForeignKey(Area, on_delete=models.SET_NULL, null=True)
    request_time = models.DateTimeField(auto_now_add=True)
    actual_time = models.DateTimeField(null=True, blank=True)
    payment_time = models.DateTimeField(null=True, blank=True)
    proposed_time = models.DateTimeField(null=True, blank=True)
    delay_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Pending")
    def __str__(self):
        return str(self.id)

class Ewaste(models.Model):
    waste_type = models.CharField(max_length=50)
    category = models.CharField(max_length=50,default='Electronic')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    def __str__(self):
        return self.waste_type

class Feedback(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    rating = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return str(self.user)


class PickupTransaction(models.Model):
    STATUS_CHOICES = [
        ("Collected","Collected"),
        ("Verified","Verified"),
        ("Rejected","Rejected"),
        ("Transferred","Transferred"),
    ]
    pickup = models.ForeignKey(Pickup, on_delete=models.CASCADE)
    waste = models.ForeignKey(Ewaste, on_delete=models.CASCADE)
    recycling_hub = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    waste_quantity = models.IntegerField()
    total_amount = models.DecimalField(max_digits=10, decimal_places=2,default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Collected")
    transaction_time = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return str(self.id)
    
class Agent(models.Model):
    STATUS_CHOICES = [
        ("Active","Active"),
        ("Inactive","Inactive"),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    vehicle_no = models.CharField(max_length=20)
    license_no = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Active")
    joining_date = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return str(self.user)
    
class AgentLocation(models.Model):
    agent = models.OneToOneField(User,on_delete=models.CASCADE)
    latitude = models.FloatField()
    longitude = models.FloatField()
    updated_at = models.DateTimeField(auto_now=True)
    
class Report(models.Model):
    report_type = models.CharField(max_length=50)
    file_path = models.CharField(max_length=200)
    FORMAT_CHOICES = [
        ("pdf", "PDF"),
        ("excel", "Excel"),
        ("csv", "CSV"),
    ]
    format = models.CharField(
        max_length=20,
        choices=FORMAT_CHOICES,
        default="pdf"
    )
    data_summary = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    generated_datetime = models.DateTimeField(auto_now_add=True)
    admin = models.ForeignKey(User, on_delete=models.CASCADE,null=True,blank=True,)
    hub= models.ForeignKey(User, on_delete=models.CASCADE,null=True,blank=True,related_name="hub_report")

    def __str__(self):
        return f"{self.report_type} - {self.id}"
    
class Salary(models.Model):
    STATUS_CHOICES = [
        ("Pending","Pending"),
        ("Paid","Paid"),
        ("Failed","Failed"),
    ]
    agent = models.ForeignKey(User, on_delete=models.CASCADE)
    month = models.CharField(max_length=20)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Pending")
    def __str__(self):
        return str(self.agent)
    
class SalaryTransaction(models.Model):
    STATUS_CHOICES = [
        ('Success', 'Success'),
        ('Failed',  'Failed'),
    ]
    salary         = models.OneToOneField(Salary, on_delete=models.CASCADE, related_name='transaction')
    transaction_id = models.CharField(max_length=50, unique=True)
    gateway        = models.CharField(max_length=50, default='Mock')
    status         = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Success')
    created_at     = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"{self.transaction_id} — {self.salary.agent.username}"
 
class Settlement(models.Model):
    recycling_hub = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    settlement_date = models.DateTimeField(auto_now_add=True)
    status = models.TextField(null=True, blank=True)
    payer_name = models.CharField(max_length=50)
    def __str__(self):
        return str(self.id)
    
class Payment(models.Model):
    STATUS_CHOICES = [
        ("Pending","Pending"),
        ("Paid","Paid"),
        ("Failed","Failed"),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    pickup = models.ForeignKey(Pickup, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Pending")
    payment_date = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return str(self.id)
    
class PaymentTransaction(models.Model):
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE)
    transaction_id = models.CharField(max_length=100)
    gateway = models.CharField(max_length=50)
    status = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return self.transaction_id
