from django.shortcuts import redirect,render
def role_required(allowd_roles=[]):
    def decorator(view_func):
        def wrapper(request,*args, **kwargs):
            role=request.session.get("role")
            if role not in allowd_roles:
                return render(request,"403.html")
            return view_func(request,*args,**kwargs)
        return wrapper
    return decorator