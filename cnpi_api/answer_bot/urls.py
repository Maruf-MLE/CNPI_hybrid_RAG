from django.urls import path

from answer_bot import views

urlpatterns = [
    # Answer Bot webhook — handles both GET (verification) and POST (events)
    path("answer-webhook/", views.answer_webhook_view, name="answer-bot-webhook"),
    path("answer-webhook", views.answer_webhook_view, name="answer-bot-webhook-noslash"),
]
