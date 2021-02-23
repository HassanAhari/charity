from rest_framework import status, generics
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated, SAFE_METHODS
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsCharityOwner, IsBenefactor
from charities.models import Task
from charities.serializers import (
    TaskSerializer, CharitySerializer, BenefactorSerializer
)


class BenefactorRegistration(generics.CreateAPIView):
    permission_classes = (IsAuthenticated, )

    def post(self, request, *args, **kwargs):
        benefactor_serializer = BenefactorSerializer(data=request.data)
        if benefactor_serializer.is_valid():
            benefactor_serializer.save(user=request.user)
            return Response({'message': 'success'})
        return Response({'message': benefactor_serializer.errors})


class CharityRegistration(APIView):
    permission_classes = (IsAuthenticated, )

    def post(self, request):
        charity_serializer = CharitySerializer(data=request.data)
        if charity_serializer.is_valid():
            charity_serializer.save(user=request.user)
            return Response({'message': 'success'})
        return Response({'message': charity_serializer.errors})


class Tasks(generics.ListCreateAPIView):
    serializer_class = TaskSerializer

    def get_queryset(self):
        return Task.objects.all_related_tasks_to_user(self.request.user)

    def post(self, request, *args, **kwargs):
        data = {
            **request.data,
            "charity_id": request.user.charity.id
        }
        serializer = self.serializer_class(data = data)
        serializer.is_valid(raise_exception = True)
        serializer.save()
        return Response(serializer.data, status = status.HTTP_201_CREATED)

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            self.permission_classes = [IsAuthenticated, ]
        else:
            self.permission_classes = [IsCharityOwner, ]

        return [permission() for permission in self.permission_classes]

    def filter_queryset(self, queryset):
        filter_lookups = {}
        for name, value in Task.filtering_lookups:
            param = self.request.GET.get(value)
            if param:
                filter_lookups[name] = param
        exclude_lookups = {}
        for name, value in Task.excluding_lookups:
            param = self.request.GET.get(value)
            if param:
                exclude_lookups[name] = param

        return queryset.filter(**filter_lookups).exclude(**exclude_lookups)


class TaskRequest(APIView):
    permission_classes = (IsBenefactor, )

    def get(self, request, task_id):
        task = get_object_or_404(Task, id=task_id)
        if task != 404:
            if task.state == Task.TaskStatus.PENDING:
                task.assign_to_benefactor(request.user.benefactor)
                return Response({'detail': 'Request sent.'}, status=200)
            return Response({'detail': 'This task is not pending.'}, status=404)
        return Response({'detail': 'You do not have access'}, status=404)


class TaskResponse(APIView):
    permission_classes = (IsCharityOwner, )

    def post(self, request, task_id):
        task = get_object_or_404(Task, id=task_id)
        if task == 404:
            return Response({'detail': 'error'}, status=404)

        response = request.data['response']
        if response != 'A' and response != 'R':
            return Response({'detail': 'Required field ("A" for accepted / "R" for rejected)'}, status=400)

        if task.state != Task.TaskStatus.WAITING:
            print('hello')
            return Response({'detail': 'This task is not waiting.'}, status=404)

        if response == 'A':
            task.response_to_benefactor_request('A')
            return Response({'detail': 'Response sent.'}, status=200)

        if response == 'R':
            task.response_to_benefactor_request('R')
            return Response({'detail': 'Response sent.'}, status=200)


class DoneTask(APIView):
    permission_classes = (IsCharityOwner, )

    def post(self, request, task_id):
        task = get_object_or_404(Task, id=task_id)
        if task == 404:
            return Response({'detail': 'error'}, status=404)

        if task.state != Task.TaskStatus.ASSIGNED:
            return Response({'detail': 'Task is not assigned yet.'}, status=404)

        task.done()
        return Response({'detail': 'Task has been done successfully.'}, status=200)
