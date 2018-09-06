
#Encargado de ejecutar una nueva compra. Por ahora no hace demasiado
def new_payment(compra):
        compra.status = 'accepted'
        compra.save()
