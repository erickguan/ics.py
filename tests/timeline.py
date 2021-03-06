import unittest
from datetime import datetime

from ics.event import Event
from ics.icalendar import Calendar
from ics.timeline import Timeline


class TestTimeline(unittest.TestCase):

    def test_type(self):

        c = Calendar()
        self.assertIsInstance(c.timeline, Timeline)

    def test_iter_is_ordered(self):
        c = Calendar()
        c.events.append(Event(begin=datetime.fromtimestamp(1236)))
        c.events.append(Event(begin=datetime.fromtimestamp(1235)))
        c.events.append(Event(begin=datetime.fromtimestamp(1234)))

        last = None
        for event in c.timeline:
            if last is not None:
                self.assertGreaterEqual(event, last)
            last = event

    def test_iter_over_all(self):
        c = Calendar()
        c.events.append(Event(begin=datetime.fromtimestamp(1234)))
        c.events.append(Event(begin=datetime.fromtimestamp(1235)))
        c.events.append(Event(begin=datetime.fromtimestamp(1236)))

        i = 0
        for event in c.timeline:
            i += 1

        self.assertEqual(i, 3)

    def test_iter_does_not_show_undefined_events(self):
        c = Calendar()

        empty = Event()
        c.events.append(empty)
        c.events.append(Event(begin=datetime.fromtimestamp(1234)))
        c.events.append(Event(begin=datetime.fromtimestamp(1235)))

        for event in c.timeline:
            self.assertIsNot(empty, event)

    def test_included(self):

        c = Calendar()

        e = [
            Event(begin=datetime(2015, 10, 10)),
            Event(begin=datetime(2010, 10, 10)),
            Event(begin=datetime(2020, 10, 10)),
            Event(begin=datetime(2015, 1, 10)),
            Event(begin=datetime(2014, 1, 10), end=datetime(2018, 1, 10)),
        ]

        for ev in e:
            c.events.append(ev)

        included = list(c.timeline.included(
            (datetime(2013, 10, 10)),
            (datetime(2017, 10, 10))
        ))
        self.assertSequenceEqual(included, [e[3]] + [e[0]])

    def test_overlapping(self):
        c = Calendar()

        e = [
            Event(begin=datetime(2010, 10, 10), end=datetime(2012, 10, 10)),
            Event(begin=datetime(2013, 10, 10), end=datetime(2014, 10, 10)),
            Event(begin=datetime(2016, 10, 10), end=datetime(2017, 10, 10)),
        ]

        for ev in e:
            c.events.append(ev)

        overlap = list(c.timeline.overlapping(
            (datetime(2011, 10, 10)),
            (datetime(2015, 10, 10))
        ))
        self.assertSequenceEqual(overlap, [e[0]] + [e[1]])

    def test_on(self):

        c = Calendar()

        e = [
            Event(begin=datetime(2015, 10, 10)),
            Event(begin=datetime(2010, 10, 10)),
            Event(begin=datetime(2020, 10, 10)),
            Event(begin=datetime(2015, 1, 10)),
            Event(begin=datetime(2014, 1, 10), end=datetime(2018, 1, 10)),
        ]

        for ev in e:
            c.events.append(ev)

        now = (datetime(2015, 10, 10, 12))
        on = list(c.timeline.on(now))
        self.assertSequenceEqual(on, [e[4], e[0]])

    def test_on_strict(self):

        c = Calendar()

        e = [
            Event(begin=datetime(2015, 10, 10)),
            Event(begin=datetime(2010, 10, 10)),
            Event(begin=datetime(2020, 10, 10)),
            Event(begin=datetime(2015, 1, 10)),
            Event(begin=datetime(2014, 1, 10), end=datetime(2018, 1, 10)),
        ]

        for ev in e:
            c.events.append(ev)

        now = (datetime(2015, 10, 10, 12))
        on = list(c.timeline.on(now, strict=True))
        self.assertSequenceEqual(on, [e[0]])
