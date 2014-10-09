# Based on https://djangosnippets.org/snippets/998/

from django.conf.urls import patterns, url
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseRedirect
from django.db import models, transaction


class OrderedModel(models.Model):
    order = models.PositiveIntegerField(editable=False)

    def save(self, **kwargs):
        if not self.id:
            try:
                self.order = self.__class__.objects.all().order_by('-order')[0].order + 1
            except IndexError:
                self.order = 0
        super(OrderedModel, self).save(**kwargs)

    def order_link(self):
        model_type_id = ContentType.objects.get_for_model(self.__class__).id
        model_id = self.id
        kwargs = {'direction': 'up', 'model_type_id': model_type_id, 'model_id': model_id}
        url_up = reverse('admin-move', kwargs=kwargs)
        kwargs['direction'] = 'down'
        url_down = reverse('admin-move', kwargs=kwargs)
        return '<a href="%s">up</a> | <a href="%s">down</a>' % (url_up, url_down)
    order_link.allow_tags = True
    order_link.short_description = 'Move'
    order_link.admin_order_field = 'order'

    @staticmethod
    def move_down(model_type_id, model_id):
        try:
            ModelClass = ContentType.objects.get(id=model_type_id).model_class()

            lower_model = ModelClass.objects.get(id=model_id)
            higher_model = ModelClass.objects.filter(order__gt=lower_model.order).order_by('order')[0]
            
            lower_model.order, higher_model.order = higher_model.order, lower_model.order

            higher_model.save()
            lower_model.save()
        except IndexError:
            pass
        except ObjectDoesNotExist:
            pass
                
    @staticmethod
    def move_up(model_type_id, model_id):
        try:
            ModelClass = ContentType.objects.get(id=model_type_id).model_class()

            higher_model = ModelClass.objects.get(id=model_id)
            lower_model = ModelClass.objects.filter(order__lt=higher_model.order).order_by('-order')[0]

            lower_model.order, higher_model.order = higher_model.order, lower_model.order

            higher_model.save()
            lower_model.save()
        except IndexError:
            pass
        except ObjectDoesNotExist:
            pass

    class Meta:
        ordering = ['order']
        abstract = True


@staff_member_required
@transaction.atomic()
def admin_move_ordered_model(request, direction, model_type_id, model_id):
    if direction == 'up':
        OrderedModel.move_up(model_type_id, model_id)
    else:
        OrderedModel.move_down(model_type_id, model_id)
    
    ModelClass = ContentType.objects.get(id=model_type_id).model_class()
    
    app_label = ModelClass._meta.app_label
    model_name = ModelClass.__name__.lower()

    return HttpResponseRedirect('/admin/%s/%s/' % (app_label, model_name))


urls = patterns('',
    url(r'^admin/orderedmove/(?P<direction>up|down)/(?P<model_type_id>\d+)/(?P<model_id>\d+)/$',
        admin_move_ordered_model, name='admin-move'),
)