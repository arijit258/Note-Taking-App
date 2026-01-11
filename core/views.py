from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from .models import Note, SharedAccess, NoteVersion, ActivityLog
from .forms import NoteForm, ShareNoteForm, RegisterForm


def register(request):
    """User registration view"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Account created successfully!')
            return redirect('dashboard')
    else:
        form = RegisterForm()
    
    return render(request, 'core/register.html', {'form': form})


@login_required
def dashboard(request):
    """Main dashboard showing user's notes and shared notes"""
    my_notes = Note.objects.filter(owner=request.user)
    shared_with_me = Note.objects.filter(shared_access__user=request.user)
    
    context = {
        'my_notes': my_notes,
        'shared_notes': shared_with_me,
    }
    return render(request, 'core/dashboard.html', context)


@login_required
def note_create(request):
    """Create a new note"""
    if request.method == 'POST':
        form = NoteForm(request.POST)
        if form.is_valid():
            # Save the form first to get updated content
            note = form.save(commit=False)
            note.owner = request.user
            note.save()
            
            # Create initial version after saving
            NoteVersion.objects.create(
                note=note,
                title=note.title,
                content=note.content,
                created_by=request.user,
                version_number=1
            )
            
            # Log activity
            ActivityLog.objects.create(
                note=note,
                user=request.user,
                action='created'
            )
            
            messages.success(request, 'Note created successfully!')
            return redirect('note_detail', pk=note.pk)
    else:
        form = NoteForm()
    
    return render(request, 'core/note_form.html', {'form': form, 'action': 'Create'})


@login_required
def note_detail(request, pk):
    """View note details"""
    note = get_object_or_404(Note, pk=pk)
    
    # Check access
    is_owner = note.owner == request.user
    shared_access = SharedAccess.objects.filter(note=note, user=request.user).first()
    
    if not is_owner and not shared_access:
        messages.error(request, 'You do not have access to this note.')
        return redirect('dashboard')
    
    can_edit = is_owner or (shared_access and shared_access.role == 'editor')
    
    # Get collaborators
    collaborators = SharedAccess.objects.filter(note=note).select_related('user')
    
    # Get version history
    versions = NoteVersion.objects.filter(note=note).order_by('-version_number')[:10]
    
    # Get activity log
    activities = ActivityLog.objects.filter(note=note).order_by('-created_at')[:10]
    
    context = {
        'note': note,
        'is_owner': is_owner,
        'can_edit': can_edit,
        'collaborators': collaborators,
        'versions': versions,
        'activities': activities,
    }
    return render(request, 'core/note_detail.html', context)


@login_required
def note_edit(request, pk):
    """Edit a note"""
    note = get_object_or_404(Note, pk=pk)
    
    # Check access
    is_owner = note.owner == request.user
    shared_access = SharedAccess.objects.filter(note=note, user=request.user).first()
    can_edit = is_owner or (shared_access and shared_access.role == 'editor')
    
    if not can_edit:
        messages.error(request, 'You do not have permission to edit this note.')
        return redirect('note_detail', pk=pk)
    
    if request.method == 'POST':
        form = NoteForm(request.POST, instance=note)
        if form.is_valid():
            # Save the form first to get updated content
            note = form.save()
            
            # Create version with new content after saving
            last_version = NoteVersion.objects.filter(note=note).order_by('-version_number').first()
            version_num = (last_version.version_number + 1) if last_version else 1
            
            NoteVersion.objects.create(
                note=note,
                title=note.title,
                content=note.content,
                created_by=request.user,
                version_number=version_num
            )
            
            # Log activity
            ActivityLog.objects.create(
                note=note,
                user=request.user,
                action='updated'
            )
            
            messages.success(request, 'Note updated successfully!')
            return redirect('note_detail', pk=pk)
    else:
        form = NoteForm(instance=note)
    
    return render(request, 'core/note_form.html', {'form': form, 'note': note, 'action': 'Edit'})


@login_required
def note_delete(request, pk):
    """Delete a note"""
    note = get_object_or_404(Note, pk=pk)
    
    if note.owner != request.user:
        messages.error(request, 'Only the owner can delete this note.')
        return redirect('note_detail', pk=pk)
    
    if request.method == 'POST':
        note.delete()
        messages.success(request, 'Note deleted successfully!')
        return redirect('dashboard')
    
    return render(request, 'core/note_confirm_delete.html', {'note': note})


@login_required
def note_share(request, pk):
    """Share a note with another user"""
    note = get_object_or_404(Note, pk=pk)
    
    if note.owner != request.user:
        messages.error(request, 'Only the owner can share this note.')
        return redirect('note_detail', pk=pk)
    
    if request.method == 'POST':
        form = ShareNoteForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            role = form.cleaned_data['role']
            
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                messages.error(request, 'User not found.')
                return redirect('note_detail', pk=pk)
            except User.MultipleObjectsReturned:
                messages.error(request, 'Multiple users found with this username. Please contact support.')
                return redirect('note_detail', pk=pk)
            
            if user == request.user:
                messages.warning(request, 'You cannot share a note with yourself.')
            else:
                shared, created = SharedAccess.objects.update_or_create(
                    note=note,
                    user=user,
                    defaults={'role': role}
                )
                
                ActivityLog.objects.create(
                    note=note,
                    user=request.user,
                    action='shared',
                    details=f'Shared with {username} as {role}'
                )
                
                if created:
                    messages.success(request, f'Note shared with {username} as {role}.')
                else:
                    messages.success(request, f'Updated {username}\'s access to {role}.')
            
            return redirect('note_detail', pk=pk)
    else:
        form = ShareNoteForm()
    
    collaborators = SharedAccess.objects.filter(note=note).select_related('user')
    
    return render(request, 'core/note_share.html', {
        'note': note,
        'form': form,
        'collaborators': collaborators
    })


@login_required
def note_unshare(request, pk, user_id):
    """Remove a user's access to a note"""
    note = get_object_or_404(Note, pk=pk)
    
    if note.owner != request.user:
        messages.error(request, 'Only the owner can manage sharing.')
        return redirect('note_detail', pk=pk)
    
    user = get_object_or_404(User, pk=user_id)
    shared = SharedAccess.objects.filter(note=note, user=user).first()
    
    if shared:
        shared.delete()
        ActivityLog.objects.create(
            note=note,
            user=request.user,
            action='unshared',
            details=f'Removed {user.username}\'s access'
        )
        messages.success(request, f'Removed {user.username}\'s access.')
    
    return redirect('note_share', pk=pk)


@login_required
def note_restore_version(request, pk, version_id):
    """Restore a previous version of a note"""
    note = get_object_or_404(Note, pk=pk)
    version = get_object_or_404(NoteVersion, pk=version_id, note=note)
    
    is_owner = note.owner == request.user
    shared_access = SharedAccess.objects.filter(note=note, user=request.user).first()
    can_edit = is_owner or (shared_access and shared_access.role == 'editor')
    
    if not can_edit:
        messages.error(request, 'You do not have permission to restore versions.')
        return redirect('note_detail', pk=pk)
    
    # Create a new version with current state before restoring
    last_version = NoteVersion.objects.filter(note=note).order_by('-version_number').first()
    version_num = (last_version.version_number + 1) if last_version else 1
    
    NoteVersion.objects.create(
        note=note,
        title=note.title,
        content=note.content,
        created_by=request.user,
        version_number=version_num
    )
    
    # Restore the old version
    note.title = version.title
    note.content = version.content
    note.save()
    
    ActivityLog.objects.create(
        note=note,
        user=request.user,
        action='restored',
        details=f'Restored to version {version.version_number}'
    )
    
    messages.success(request, f'Note restored to version {version.version_number}.')
    return redirect('note_detail', pk=pk)


@login_required
def user_search(request):
    """Search for users by username (AJAX endpoint)"""
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'users': []})
    
    # Search users by username (case-insensitive)
    users = User.objects.filter(
        username__icontains=query
    ).exclude(
        username=request.user.username
    ).values('id', 'username', 'email')[:10]
    
    return JsonResponse({'users': list(users)})
