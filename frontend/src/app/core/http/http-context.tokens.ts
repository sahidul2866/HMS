import { HttpContextToken } from '@angular/common/http';

export const SKIP_GLOBAL_LOADER = new HttpContextToken<boolean>(() => false);
