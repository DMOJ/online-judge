import calendar, datetime
from judge.models import Contest, ContestParticipation, ContestProblem, Profile


class MyCal(calendar.HTMLCalendar):
    def __init__(self, x):
        super(MyCal, self).__init__(x)
        self.today = datetime.datetime.date(datetime.datetime.now())

    def formatweekday(self, day):
        return '<th class="%s">%s</th>' % (self.cssclasses[day], calendar.day_name[day])

    def formatday(self, day, weekday):
        if day == 0:
            return '<td class="noday">&nbsp;</td>'  # day outside month
        elif day == self.today.day:
            return '<td class="%s today"><span class="num">%d</span></td>' % (self.cssclasses[weekday], day)
        elif day == 19:
            return '<td class="%s"><span class="num">%d</span>%s</td>'
        else:
            c = '<ul>'

            for c in Contest.objects.filter(start_time__month=self.today.month, start_time__day=day):
                c += '<li class=\'%s\'><a href=\'#\'>%s</a></li>' % (
                    'oneday' if (c.end_time.day == day and c.end_time.month == self.today.month) else 'starting',
                    c.name)
            for c in Contest.objects.filter(end_time__month=self.today.month, end_time__day=day):
                c += '<li class=\'%s\'><a href=\'#\'>%s</a></li>' % ('ending', c.name)
            c += '<ul>'
            return '<td class="%s"><span class="num">%d</span>%s</td>' % (self.cssclasses[weekday], day, c)


today = datetime.datetime.date(datetime.datetime.now())

print '''
<head>
<style>
th.sun, th.mon, th.tue, th.wed, th.thu, th.fri, th.sat {
  font-size:0.95em;
  border-right:1px solid #aaa;
  background:#f2f2f2;
}

th.sun {
  border-left:1px solid #aaa;
}

td .num {
  font-size:1.1em;
  font-weight:bold;
  display:block;
  border-bottom:1px dashed #ccc;
  padding-right:0.2em;
  margin-bottom:0.4em;
}

td ul li a {
  text-decoration: none;
  color:#222;
}

td:hover ul li a {
  font-weight: normal;
}

td ul li a:hover {
  text-decoration: underline;
}

td ul {
  text-decoration: none;
  list-style-type: none;
  text-align: left;
  padding:0;
  margin:0;
}

td ul li {
  background-image: url('http://dev.ivybits.tk/images/bullet_diamond.png'); background-repeat: no-repeat;
  background-position: 1px 1px; 
  padding-left:17px;
  margin-bottom:0.2em;
}

td {
  height:110px;
  width:161px;
  color:#000;
  vertical-align:top;
  text-align:right;
  font-size:0.75em;
}

td {
  border-right:1px solid #aaa;
  border-bottom:1px solid #aaa;
  transition-duration:0.2s;
}

td:hover {
  background: rgba(0,0,255,0.3);
  color:white;
}

td:hover .num {
  font-weight: bold;
}

tr td:first-child {
  border-left:1px solid #aaa;
}

th {
  border-bottom:1px solid #aaa;
}

.noday {
  background:#f1f1f1;
}

.today {
  background: rgba(255,255,100,0.5);
}

</style></head>'''

cal = MyCal(calendar.SUNDAY)
print cal.formatmonth(today.year, today.month)