import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { Expense, ImportedExpense } from '@/lib/api';

interface ExpensesState {
  expenses: Expense[];
  importedExpenses: ImportedExpense[];
  isLoading: boolean;
}

const initialState: ExpensesState = {
  expenses: [],
  importedExpenses: [],
  isLoading: false,
};

const expensesSlice = createSlice({
  name: 'expenses',
  initialState,
  reducers: {
    setExpenses: (state, action: PayloadAction<Expense[]>) => {
      state.expenses = action.payload;
    },
    setImportedExpenses: (state, action: PayloadAction<ImportedExpense[]>) => {
      state.importedExpenses = action.payload;
    },
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.isLoading = action.payload;
    },
  },
});

export const { setExpenses, setImportedExpenses, setLoading } = expensesSlice.actions;
export default expensesSlice.reducer;
