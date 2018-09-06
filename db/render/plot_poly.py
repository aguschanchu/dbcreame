from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
import random, string, matplotlib, io
import numpy as np
from django.core.files.base import ContentFile

def polyplot(polinomio):
        f = matplotlib.figure.Figure()
        buf = io.BytesIO()
        canvas = FigureCanvasAgg(f)
        ax = f.add_subplot(111)
        p = np.poly1d(polinomio.coefficients_list())
        x = np.arange(0.1,2,.05)
        y = [y/3600 for y in np.polyval(p,x)]
        ax.plot(x, y)
        canvas.print_png(buf)
        polinomio.plot.save(''.join(random.choices(string.ascii_uppercase + string.digits, k=8))+'.png',ContentFile(buf.getvalue()),save=False)
        polinomio.save(update_fields=['plot'])
