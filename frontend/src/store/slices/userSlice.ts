import { createSlice, PayloadAction } from '@reduxjs/toolkit';

interface UserState {
  email: string | null;
  id: string | null;
  isAuthenticated: boolean;
}

const initialState: UserState = {
  email: null,
  id: null,
  isAuthenticated: false,
};

const userSlice = createSlice({
  name: 'user',
  initialState,
  reducers: {
    setUser: (state, action: PayloadAction<{ email: string; id: string }>) => {
      state.email = action.payload.email;
      state.id = action.payload.id;
      state.isAuthenticated = true;
    },
    clearUser: (state) => {
      state.email = null;
      state.id = null;
      state.isAuthenticated = false;
    },
  },
});

export const { setUser, clearUser } = userSlice.actions;
export default userSlice.reducer;
