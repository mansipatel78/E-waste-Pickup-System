from django.shortcuts import redirect
class LoginRequiredMiddleware:
    def __init__(self,get_response):
        self.get_response=get_response
    def __call__(self, request):
        open_urls=['/login/','/signup/','/forgot/','/reset/','/']
        if not request.path.startswith('/static/'):
            if not any(request.path.startswith(url) for url in open_urls):
                if not request.session.get('user_id'):
                    return redirect("login")
        return self.get_response(request)