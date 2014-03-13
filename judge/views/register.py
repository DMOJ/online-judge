from registration.views import RegistrationView, ActivationView


class RegistrationView(RegistrationView):
    title = 'Registration'

    def get_context_data(self, **kwargs):
        if 'title' not in kwargs:
            kwargs['title'] = self.title
        return super(RegistrationView, self).get_context_data(**kwargs)


class ActivationView(ActivationView):
    title = 'Registration'

    def get_context_data(self, **kwargs):
        if 'title' not in kwargs:
            kwargs['title'] = self.title
        return super(ActivationView, self).get_context_data(**kwargs)
