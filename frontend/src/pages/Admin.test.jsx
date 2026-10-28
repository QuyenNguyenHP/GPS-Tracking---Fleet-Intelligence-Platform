import React from 'react';
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen, waitFor} from '@testing-library/react';
import Admin from './Admin';
import {request} from '../services/api';

vi.mock('../services/api', () => ({request: vi.fn()}));
const organizations = [{id: 'demo', name: 'Demo Company', enabled: true}, {id: 'other', name: 'Other Company', enabled: false}];
const users = [{id: 'u1', username: 'admin', name: 'Admin User', enabled: true, is_platform_admin: true, organization_ids: ['demo']}];
const auth = {token: 'test-session', organization: 'demo', user: {...users[0], organizations}};
const refreshProfile = vi.fn();

beforeEach(() => {
  vi.clearAllMocks();
  HTMLDialogElement.prototype.showModal = function() {this.open = true;};
  HTMLDialogElement.prototype.close = function() {this.open = false;};
  request.mockImplementation(async (path, _auth, options) => {
    if (options) return {};
    return path.endsWith('/organizations') ? organizations : users;
  });
});
afterEach(cleanup);

async function mount() {
  render(<Admin auth={auth} logout={vi.fn()} openFleet={vi.fn()} refreshProfile={refreshProfile}/>);
  await screen.findByText('Demo Company');
}

describe('Platform administration forms', () => {
  it('creates an organization with a stable ID', async () => {
    await mount();
    fireEvent.click(screen.getByRole('button', {name: '+ Create organization'}));
    fireEvent.change(screen.getByLabelText('Organization ID'), {target: {value: 'new-org'}});
    fireEvent.change(screen.getByLabelText('Organization name'), {target: {value: 'New organization'}});
    fireEvent.click(screen.getByRole('button', {name: 'Save changes'}));
    await waitFor(() => expect(request).toHaveBeenCalledWith('/admin/organizations', auth, {
      method: 'POST', body: JSON.stringify({name: 'New organization', enabled: true, id: 'new-org'}),
    }));
    await screen.findByRole('status');
  });

  it('creates an account with selected workspace access', async () => {
    await mount();
    fireEvent.click(screen.getByRole('tab', {name: 'Users'}));
    fireEvent.click(screen.getByRole('button', {name: '+ Create account'}));
    fireEvent.change(screen.getByLabelText('Username'), {target: {value: 'dispatcher'}});
    fireEvent.change(screen.getByLabelText('Display name'), {target: {value: 'Dispatcher'}});
    fireEvent.change(screen.getByLabelText('Password'), {target: {value: 'test-password-long'}});
    fireEvent.click(screen.getByLabelText('Demo Company'));
    fireEvent.click(screen.getByRole('button', {name: 'Save changes'}));
    await waitFor(() => expect(request).toHaveBeenCalledWith('/admin/users', auth, {
      method: 'POST', body: JSON.stringify({username: 'dispatcher', name: 'Dispatcher', password: 'test-password-long', enabled: true, is_platform_admin: false, organization_ids: ['demo']}),
    }));
  });

  it('protects own admin role and omits a blank password when editing', async () => {
    await mount();
    fireEvent.click(screen.getByRole('tab', {name: 'Users'}));
    fireEvent.click(screen.getByRole('button', {name: 'Edit account'}));
    expect(screen.getByLabelText('Account enabled').disabled).toBe(true);
    expect(screen.getByLabelText(/Platform administrator —/).disabled).toBe(true);
    fireEvent.change(screen.getByLabelText('Display name'), {target: {value: 'Updated admin'}});
    fireEvent.click(screen.getByRole('button', {name: 'Save changes'}));
    await waitFor(() => {
      const call = request.mock.calls.find(([path, , options]) => path === '/admin/users/u1' && options);
      expect(call).toBeTruthy();
      expect(JSON.parse(call[2].body)).toEqual({name: 'Updated admin', enabled: true, is_platform_admin: true, organization_ids: ['demo']});
    });
  });

  it('keeps the form and displays server validation failures', async () => {
    await mount();
    fireEvent.click(screen.getByRole('button', {name: '+ Create organization'}));
    fireEvent.change(screen.getByLabelText('Organization ID'), {target: {value: 'demo'}});
    fireEvent.change(screen.getByLabelText('Organization name'), {target: {value: 'Duplicate'}});
    request.mockRejectedValueOnce(new Error('This organization ID already exists'));
    fireEvent.click(screen.getByRole('button', {name: 'Save changes'}));
    expect((await screen.findByRole('alert')).textContent).toContain('already exists');
    expect(screen.getByRole('dialog')).toBeTruthy();
  });
});
